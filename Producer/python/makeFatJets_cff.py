import re
import FWCore.ParameterSet.Config as cms
from RecoJets.JetProducers.ak4PFJets_cfi import ak4PFJets
from RecoJets.JetProducers.ak4GenJets_cfi import ak4GenJets
import RecoJets.JetProducers.nJettinessAdder_cfi as nJettinessAdder_cfi
from RecoJets.JetProducers.QGTagger_cfi import QGTagger
from PhysicsTools.PatAlgos.producersLayer1.jetProducer_cfi import _patJets
import PhysicsTools.PatAlgos.selectionLayer1.jetSelector_cfi as jetSelector_cfi
import PhysicsTools.PatAlgos.producersLayer1.jetUpdater_cff as jetUpdater_cff
from PhysicsTools.PatAlgos.mcMatchLayer0.jetMatch_cfi import patJetGenJetMatch
#from PhysicsTools.PatAlgos.tools.jetTools import updateJetCollection

from ECFTest.Producer.addattr import AddAttr

finalStateGenParticles = 'packedGenParticles'
prunedGenParticles = 'prunedGenParticles'
pfSource = 'packedPFCandidates'
pvSource = 'offlineSlimmedPrimaryVertices'
svSource = 'slimmedSecondaryVertices'
muSource = 'slimmedMuons'
elSource = 'slimmedElectrons'

def sdParams(radius):
    if radius < 1.:
        sdZcut = 0.1
        sdBeta = 0.0
    else:
        sdZcut = 0.15
        sdBeta = 1.0

    return sdZcut, sdBeta

def initFatJets(process, isData, labels):
    """
    @labels: ['AK8', 'CA15', ...]
    """

    ########################################
    ##         INITIAL SETUP              ##
    ########################################
  
    sequence = cms.Sequence()

    addattr = AddAttr(process, sequence)

    if not isData and not hasattr(process, 'packedGenParticlesForJetsNoNu'):
        genParticlesNoNu = addattr('packedGenParticlesForJetsNoNu',
            cms.EDFilter("CandPtrSelector",
                src = cms.InputTag(finalStateGenParticles),
                cut = cms.string("abs(pdgId) != 12 && abs(pdgId) != 14 && abs(pdgId) != 16")
            )
        )

        for label in labels:
            matches = re.match('(AK|CA)([0-9]+)$', label)
            if not matches:
                raise RuntimeError('Unknown algo label ' + label)

            # set up radius and algoName from the input label
            radius = float(matches.group(2)) * 0.1
            if matches.group(1) == 'CA':
                algoName = 'CambridgeAachen'
            elif matches.group(1) == 'AK':
                algoName = 'AntiKt'

            # gen jets
            addattr('genJetsNoNu' + label,
                ak4GenJets.clone(
                    doAreaFastjet = cms.bool(False), # This flag is turned on by default in CMSSW and makes things much slower, do not turn this on
                    jetAlgorithm = cms.string(algoName),
                    rParam = cms.double(radius),
                    src = genParticlesNoNu
                )
            )
            genJetsMod = addattr.last

            sdZcut, sdBeta = sdParams(radius)

            # gen jets soft drop for subjet gen matching
            addattr('genJetsNoNuSoftDrop' + label,
                genJetsMod.clone(
                    R0 = cms.double(radius),
                    useSoftDrop = cms.bool(True),
                    zcut = cms.double(sdZcut),
                    beta = cms.double(sdBeta),
                    writeCompound = cms.bool(True),
                    useExplicitGhosts = cms.bool(True),
                    jetCollInstanceName=cms.string("SubJets")
                )
            )

    # Charged hadron subtraction
    if not hasattr(process, 'pfCHS'):
        addattr('pfCHS',
            cms.EDFilter("CandPtrSelector",
                src = cms.InputTag(pfSource),
                cut = cms.string("fromPV")
            )
        )

    return sequence

def makeFatJets(process, isData, label, candidates, ptMin = 100.):
    """
    @param label: AK8PFchs, CA15PFPuppi, etc.
    """

    matches = re.match('(AK|CA)([0-9]+)PF(.+)', label)
    if not matches:
        raise RuntimeError('Unknown algo label ' + label)

    algo = matches.group(1) + matches.group(2)

    # set up radius and algoName from the input label
    radius = float(matches.group(2)) * 0.1
    if matches.group(1) == 'CA':
        algoName = 'CambridgeAachen'
    elif matches.group(1) == 'AK':
        algoName = 'AntiKt'

    pu = matches.group(3)

    if pu == 'chs':
        jecLabel = 'AK8PFchs' # regardless of jet algo
    elif pu == 'Puppi':
        jecLabel = 'AK8PFPuppi' # regardless of jet algo
    else:
        raise RuntimeError('Unknown PU mitigation ' + pu)

    sdZcut, sdBeta = sdParams(radius)

    sequence = cms.Sequence()

    # Callable object that adds the second argument to process and sequence with label attached as suffix
    addattr = AddAttr(process, sequence, label)
 
    ########################################
    ##           REMAKE JETS              ##
    ########################################

    pfJets = addattr('pfJets',
        ak4PFJets.clone(
            doAreaFastjet = cms.bool(False), # This flag is turned on by default in CMSSW and makes things much slower, do not turn this on
            jetAlgorithm = cms.string(algoName),
            rParam = cms.double(radius),
            src = cms.InputTag(candidates),
            jetPtMin = cms.double(ptMin)
        )
    )

    pfJetsSoftDrop = addattr('pfJetsSoftDrop',
        ak4PFJets.clone(
            doAreaFastjet = cms.bool(False), # This flag is turned on by default in CMSSW and makes things much slower, do not turn this on
            jetAlgorithm = cms.string(algoName),
            rParam = cms.double(radius),
            src = cms.InputTag(candidates),
            jetPtMin = cms.double(ptMin),
            useSoftDrop = cms.bool(True),
            R0 = cms.double(radius),
            zcut = cms.double(sdZcut),
            beta = cms.double(sdBeta),
            writeCompound = cms.bool(True),
            useExplicitGhosts = cms.bool(True),
            jetCollInstanceName = cms.string("SubJets")
        )
    )
    subjets = cms.InputTag(pfJetsSoftDrop.getModuleLabel(), 'SubJets')

    pfJetsPruned = addattr('pfJetsPruned',
        ak4PFJets.clone(
            doAreaFastjet = cms.bool(False), # This flag is turned on by default in CMSSW and makes things much slower, do not turn this on
            jetAlgorithm = cms.string(algoName),
            rParam = cms.double(radius),
            src = cms.InputTag(candidates),
            jetPtMin = cms.double(ptMin),
            usePruning = cms.bool(True),
            useExplicitGhosts = cms.bool(True),
            writeCompound = cms.bool(True),
            zcut = cms.double(0.1),       # no idea if these parameters are correct
            rcut_factor = cms.double(0.5), 
            nFilt = cms.int32(2),
            jetCollInstanceName = cms.string("SubJets")
        )
    )
  
    ########################################
    ##           SUBSTRUCTURE             ##
    #######################################
  
    Njettiness = addattr('Njettiness',
        nJettinessAdder_cfi.Njettiness.clone(                                      
            src = pfJets,
            R0 = cms.double(radius),
            Njets = cms.vuint32(1, 2, 3, 4)
        )
    )
  
    sdKinematics = addattr('sdKinematics',
        cms.EDProducer('RecoJetDeltaRValueMapProducer',
            src = pfJets,
            matched = pfJetsSoftDrop,
            distMax = cms.double(radius),
            values = cms.vstring('mass'),
            valueLabels = cms.vstring('Mass')
        )
    )

    prunedKinematics = addattr('prunedKinematics',
        cms.EDProducer('RecoJetDeltaRValueMapProducer',
            src = pfJets,
            matched = pfJetsPruned,
            distMax = cms.double(radius),
            values = cms.vstring('mass'),
            valueLabels = cms.vstring('Mass')
        )
    )
  
    ### subjet qg-tagging ###

    subQGTag = addattr('subQGTag',
        QGTagger.clone(
            srcJets = subjets,
            jetsLabel = cms.string('QGL_AK4PFchs')
        )
    )
  
    ########################################
    ##          MAKE PAT JETS             ##
    ########################################
  
    ## MAIN JET ##

    jecLevels= ['L1FastJet',  'L2Relative', 'L3Absolute']
    if isData:
        jecLevels.append('L2L3Residual')

    jetCorrFactors = addattr('jetCorrFactors',
        jetUpdater_cff.patJetCorrFactors.clone(
            src = pfJets,
            payload = jecLabel,
            levels = jecLevels,
            primaryVertices = pvSource
        )
    )

    if not isData:
        genJetMatch = addattr('genJetMatch',
            patJetGenJetMatch.clone(
                src = pfJets,
                maxDeltaR = radius,
                matched = 'genJetsNoNu' + algo
            )
        )

    patJets = addattr('patJets',
        _patJets.clone(
            jetSource = pfJets,
            addJetCorrFactors = True,
            addBTagInfo = True,
            addAssociatedTracks = False,
            addJetCharge = False,
            addGenPartonMatch = False,
            addGenJetMatch = (not isData),
            getJetMCFlavour = False,
            addJetFlavourInfo = False
        )
    )
    patJetsMod = addattr.last
    patJetsMod.jetCorrFactorsSource = [jetCorrFactors]
    patJetsMod.discriminatorSources = []
    if not isData:
        patJetsMod.genJetMatch = genJetMatch

    for tau in ['tau1', 'tau2', 'tau3', 'tau4']:
        patJetsMod.userData.userFloats.src.append(Njettiness.getModuleLabel() + ':' + tau)

    patJetsMod.userData.userFloats.src.append(sdKinematics.getModuleLabel() + ':Mass')
    patJetsMod.userData.userFloats.src.append(prunedKinematics.getModuleLabel() + ':Mass')
    patJetsMod.userData.userFloats.labelPostfixesToStrip = cms.vstring(label)

    selectedPatJets = addattr('selectedPatJets',
        jetSelector_cfi.selectedPatJets.clone(
            src = patJets,
            cut = 'abs(eta) < 2.5'
        )
    )

    ## SOFT DROP ##

    patJetsSoftDrop = addattr('patJetsSoftDrop',
        _patJets.clone(
            jetSource = pfJetsSoftDrop,
            addJetCorrFactors = False,
            addBTagInfo = False,
            addAssociatedTracks = False,
            addJetCharge = False,
            addGenPartonMatch = False,
            addGenJetMatch = False,
            getJetMCFlavour = False,
            addJetFlavourInfo = False
        )
    )

    selectedPatJetsSoftDrop = addattr('selectedPatJetsSoftDrop',
        jetSelector_cfi.selectedPatJets.clone(
            src = patJetsSoftDrop,
            cut = 'abs(eta) < 2.5'
        )
    )

    ## GEN MATCH ##

    if not isData:
        genSubjetsMatch = addattr('genSubjetMatch',
            patJetGenJetMatch.clone(
                src = subjets,
                maxDeltaR = 0.4,
                matched = 'genJetsNoNuSoftDrop' + algo + ':SubJets'
            )
        )

    ### SUBJETS ###

    patSubjets = addattr('patSubjets',
        _patJets.clone(
            jetSource = subjets,
            addJetCorrFactors = False,
            addBTagInfo = False,
            addAssociatedTracks = False,
            addJetCharge = False,
            addGenPartonMatch = False,
            addGenJetMatch = (not isData),
            getJetMCFlavour = False,
            addJetFlavourInfo = False
        )
    )
    patSubjetsMod = addattr.last
    patSubjetsMod.userData.userFloats.src.append(cms.InputTag(subQGTag.getModuleLabel(), 'qgLikelihood'))
    patSubjetsMod.userData.userFloats.labelPostfixesToStrip = cms.vstring(label)
    if not isData:
        patSubjetsMod.genJetMatch = genSubjetsMatch

    ## MERGE SUBJETS BACK ##
    jetMerger = addattr('jetMerger',
        cms.EDProducer("BoostedJetMerger",    
            jetSrc = selectedPatJetsSoftDrop,
            subjetSrc = patSubjets
        )
    )

    ## PACK ##
    addattr('packedPatJets',
        cms.EDProducer("JetSubstructurePacker",
            jetSrc = selectedPatJets,
            distMax = cms.double(radius),
            algoTags = cms.VInputTag(
                jetMerger
            ),
            algoLabels = cms.vstring('SoftDrop'),
            fixDaughters = cms.bool(False)
        )
    )

    return sequence
