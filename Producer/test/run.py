import FWCore.ParameterSet.Config as cms
import FWCore.ParameterSet.VarParsing as VarParsing
import re
import os

process = cms.Process("test")
cmssw_base = os.environ['CMSSW_BASE']


options = VarParsing.VarParsing ('analysis')
options.register('isData',
        False,
        VarParsing.VarParsing.multiplicity.singleton,
        VarParsing.VarParsing.varType.bool,
        "True if running on Data, False if running on MC")

options.register('isGrid', False, VarParsing.VarParsing.multiplicity.singleton,VarParsing.VarParsing.varType.bool,"Set it to true if running on Grid")

options.parseArguments()
isData = options.isData

process.load("FWCore.MessageService.MessageLogger_cfi")
process.MessageLogger.cerr.FwkReport.reportEvery = 5000

process.maxEvents = cms.untracked.PSet( input = cms.untracked.int32(-1) )

if isData:
   fileList = [
       'file:/tmp/snarayan/met_miniaod.root'
       ]
else:
   fileList = [
       'file:/tmp/snarayan/zptt_miniaod.root'
       ]
### do not remove the line below!
###FILELIST###

process.source = cms.Source("PoolSource",
          skipEvents = cms.untracked.uint32(0),
          fileNames = cms.untracked.vstring(fileList)
        )

# ---- define the output file -------------------------------------------
process.TFileService = cms.Service("TFileService",
          closeFileFast = cms.untracked.bool(True),
          fileName = cms.string("test.root"),
        )

##----------------GLOBAL TAG ---------------------------
# used by photon id and jets
process.load("Configuration.Geometry.GeometryIdeal_cff") 
process.load('Configuration.StandardSequences.Services_cff')
process.load("Configuration.StandardSequences.MagneticField_cff")

#mc https://twiki.cern.ch/twiki/bin/view/CMSPublic/SWGuideFrontierConditions#Global_Tags_for_Run2_MC_Producti
process.load('Configuration.StandardSequences.FrontierConditions_GlobalTag_condDBv2_cff')
process.GlobalTag.globaltag = '94X_mc2017_realistic_v14'

### LOAD DATABASE
from CondCore.DBCommon.CondDBSetup_cfi import *

process.jetSequence = cms.Sequence()

### PUPPI
from PhysicsTools.PatAlgos.slimming.puppiForMET_cff import makePuppiesFromMiniAOD
## Creates process.puppiMETSequence which includes 'puppi' and 'puppiForMET' (= EDProducer('PuppiPhoton'))
## By default, does not use specific photon ID for PuppiPhoton (which was the case in 80X)
makePuppiesFromMiniAOD(process, createScheduledSequence = True)
## Just renaming
puppiSequence = process.puppiMETSequence

process.puppiNoLep.useExistingWeights = False
process.puppi.useExistingWeights = False


##################### FAT JETS #############################

from ECFTest.Producer.makeFatJets_cff import initFatJets, makeFatJets
fatjetInitSequence = initFatJets(process, isData, ['CA15'])
process.jetSequence += fatjetInitSequence

ca15PuppiSequence = makeFatJets(
    process,
    isData = options.isData,
    label = 'CA15PFPuppi',
    candidates = 'puppi'
)
process.jetSequence += ca15PuppiSequence

process.load('ECFTest.Producer.ecfTagger_cfi')
process.tagSequence = cms.Sequence(process.ecfTagger) 

process.dump = cms.EDAnalyzer("EventContentAnalyzer")
process.dumpSequence = cms.Sequence(process.dump)

###############################

process.p = cms.Path(	
			process.puppiMETSequence * 
                        process.jetSequence * 
#			process.dumpSequence *
			process.tagSequence
                    )
