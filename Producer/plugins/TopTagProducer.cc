#include "../interface/TopTagProducer.h"
#include "FWCore/Framework/interface/MakerMacros.h"

#define DEBUG 1

using namespace std; 
using namespace fastjet;

TopTagProducer::TopTagProducer(const edm::ParameterSet& iConfig) :
  src_(iConfig.getParameter<edm::InputTag>("src")),
  src_token_(consumes<edm::View<reco::Jet>>(src_)),
  ecfs(11)
{
  // soft drop
  int activeAreaRepeats = 1;
  double ghostArea = 0.01;
  double ghostEtaMax = 7.0;
  double radius = 1.5;
  double sdZcut = 0.15;
  double sdBeta = 1.;

  jetDef.reset(new JetDefinition(cambridge_algorithm,
                                          radius));
  activeArea.reset(new GhostedAreaSpec(ghostEtaMax,activeAreaRepeats,ghostArea));
  areaDef.reset(new AreaDefinition(active_area_explicit_ghosts,*activeArea));
  softDrop.reset(new contrib::SoftDrop(sdBeta,sdZcut,radius));

  // substructure
  tauN = make_unique<contrib::Njettiness>(contrib::OnePass_KT_Axes(), 
                                          contrib::NormalizedMeasure(1.,radius));


  ecfcalc.reset(new ECFCalculator());

  bool optimalR=true; bool doHTTQ=false;
  double minSJPt=0.; double minCandPt=0.;
  double sjmass=30.; double mucut=0.8;
  double filtR=0.3; int filtN=5;
  int mode=4; double minCandMass=0.;
  double maxCandMass=9999999.; double massRatioWidth=9999999.;
  double minM23Cut=0.; double minM13Cut=0.;
  double maxM13Cut=9999999.;  bool rejectMinR=false;
  htt.reset(new fastjet::HEPTopTaggerV2(optimalR,doHTTQ,
                                        minSJPt,minCandPt,
                                               sjmass,mucut,
                                               filtR,filtN,
                                               mode,minCandMass,
                                               maxCandMass,massRatioWidth,
                                               minM23Cut,minM13Cut,
                                               maxM13Cut,rejectMinR));

  // BDTs
  bdts["v0"] = make_unique<TMVA::Reader>();
  bdts["v0"]->AddVariable("ecfN_1_2_20/pow(ecfN_1_2_10,2.00)",&ecfs[0]);
  bdts["v0"]->AddVariable("ecfN_1_3_40/ecfN_2_3_20",&ecfs[1]);
  bdts["v0"]->AddVariable("ecfN_3_3_10/pow(ecfN_1_3_40,0.75)",&ecfs[2]);
  bdts["v0"]->AddVariable("ecfN_3_3_10/pow(ecfN_2_3_20,0.75)",&ecfs[3]);
  bdts["v0"]->AddVariable("ecfN_3_3_20/pow(ecfN_3_3_40,0.50)",&ecfs[4]);
  bdts["v0"]->AddVariable("ecfN_1_4_20/pow(ecfN_1_3_10,2.00)",&ecfs[5]);
  bdts["v0"]->AddVariable("ecfN_1_4_40/pow(ecfN_1_3_20,2.00)",&ecfs[6]);
  bdts["v0"]->AddVariable("ecfN_2_4_05/pow(ecfN_1_3_05,2.00)",&ecfs[7]);
  bdts["v0"]->AddVariable("ecfN_2_4_10/pow(ecfN_1_3_10,2.00)",&ecfs[8]);
  bdts["v0"]->AddVariable("ecfN_2_4_10/pow(ecfN_2_3_05,2.00)",&ecfs[9]);
  bdts["v0"]->AddVariable("ecfN_2_4_20/pow(ecfN_1_3_20,2.00)",&ecfs[10]);
  bdts["v0"]->AddVariable("tau32SD",&tau32sd);
  bdts["v0"]->AddVariable("htt_frec",&htt_frec);
  bdts["v0"]->AddSpectator("eventNumber",&spectator);
  bdts["v0"]->AddSpectator("runNumber",&spectator);
  bdts["v0"]->AddSpectator("pt",&spectator);
  bdts["v0"]->AddSpectator("mSD",&spectator);
  bdts["v0"]->BookMVA("v0", 
                      string(getenv("CMSSW_BASE")) 
                       + "/src/ECFTest/Producer/data/top_ecfbdt_v8_BDT.weights.xml");

  for (auto& iter : bdts) {
    produces<edm::ValueMap<float> >(("topTag" + iter.first).c_str());
  }
}

void TopTagProducer::produce(edm::Event & iEvent, const edm::EventSetup & iSetup) {
  // read input collection
  edm::Handle<edm::View<reco::Jet> > jets;
  iEvent.getByToken(src_token_, jets);
  
  map<string, vector<float>> outputVals;
  for (auto& iter : bdts) {
    outputVals[iter.first] = vector<float>(0);
    outputVals[iter.first].reserve(jets->size());
  }

  for (auto& jet : *jets) {
    reset();
    // convert the jet into pseudojet 
    vector<PseudoJet> vjet;
    for (auto&& ptr : jet.getJetConstituents()) { 
      // create vector of PseudoJets
      auto& cand(*ptr);
      if (cand.pt() < 0.01) 
        continue;
      vjet.emplace_back(cand.px(), cand.py(), cand.pz(), cand.energy());
    }

    ClusterSequenceArea seq(vjet, *jetDef, *areaDef);
    auto alljets(sorted_by_pt(seq.inclusive_jets(0.1)));
    if (alljets.size() == 0) {
      for (auto& iter : outputVals) {
        iter.second.push_back(-1.2);
      }
      continue;
    }

    // soft drop the jet 
    auto& pj(alljets[0]); 
    auto sd((*softDrop)(pj));
    auto sdConstituents(sorted_by_pt(sd.constituents()));

    // compute tauNs
    tau32sd = tauN->getTau(3, sdConstituents) / tauN->getTau(2, sdConstituents);

    // compute ECFs
    unsigned nFilter = min(100, (int)sdConstituents.size());
    vector<PseudoJet> sdConstsFiltered(sdConstituents.begin(), sdConstituents.begin() + nFilter);
    ecfcalc->calculate(sdConstsFiltered);
    ecfs[0]  = get_ecf(1,2,2) / pow(get_ecf(1,2,1),2.00);
    ecfs[1]  = get_ecf(1,3,3) / get_ecf(2,3,2);          
    ecfs[2]  = get_ecf(3,3,1) / pow(get_ecf(1,3,3),0.75);
    ecfs[3]  = get_ecf(3,3,1) / pow(get_ecf(2,3,2),0.75);
    ecfs[4]  = get_ecf(3,3,2) / pow(get_ecf(3,3,3),0.50);
    ecfs[5]  = get_ecf(1,4,2) / pow(get_ecf(1,3,1),2.00);
    ecfs[6]  = get_ecf(1,4,3) / pow(get_ecf(1,3,2),2.00);
    ecfs[7]  = get_ecf(2,4,0) / pow(get_ecf(1,3,0),2.00);
    ecfs[8]  = get_ecf(2,4,1) / pow(get_ecf(1,3,1),2.00);
    ecfs[9]  = get_ecf(2,4,1) / pow(get_ecf(2,3,0),2.00);
    ecfs[10] = get_ecf(2,4,2) / pow(get_ecf(1,3,2),2.00);

    // compute HEPTopTag
    PseudoJet httJet(htt->result(pj));
    if (httJet != 0) {
      auto* s(static_cast<fastjet::HEPTopTaggerV2Structure*>(httJet.structure_non_const_ptr()));
      htt_mass = s->top_mass();
      htt_frec = s->fRec();
    } else {
      htt_mass = 0;
      htt_frec = 0;
    }

    // compute and fill BDT
    for (auto& iter : bdts) {
      if (true) { // sanity checks
        outputVals[iter.first].push_back(iter.second->EvaluateMVA(iter.first));
      } else {
        outputVals[iter.first].push_back(-1.2); 
      }
#if DEBUG
      printf("pt=%8.3f, eta=%7.3f, msd=%8.3f bdt=%f\n", 
	     jet.pt(), jet.eta(), sd.m(), outputVals[iter.first].back());
#endif
    }
  }

  for (auto& iter : bdts) {
    auto outT = make_unique<edm::ValueMap<float>>();
    edm::ValueMap<float>::Filler fillerT(*outT);
    fillerT.insert(jets, outputVals[iter.first].begin(), outputVals[iter.first].end());
    fillerT.fill();
    iEvent.put(move(outT), ("topTag" + iter.first).c_str()); 
  }
}



DEFINE_FWK_MODULE(TopTagProducer);
