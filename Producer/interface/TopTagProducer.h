#ifndef TopTagProducer_h
#define TopTagProducer_h

#include <memory>
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/EventSetup.h"
#include "FWCore/Framework/interface/stream/EDProducer.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/Utilities/interface/InputTag.h"
#include "DataFormats/JetReco/interface/Jet.h"
#include "DataFormats/Common/interface/ValueMap.h"
#include "fastjet/PseudoJet.hh"
#include "fastjet/JetDefinition.hh"
#include "fastjet/GhostedAreaSpec.hh"
#include "fastjet/AreaDefinition.hh"
#include "fastjet/ClusterSequenceArea.hh"
#include "fastjet/contrib/Njettiness.hh"
#include "fastjet/contrib/MeasureDefinition.hh"
#include "fastjet/contrib/SoftDrop.hh"
#include "EnergyCorrelations.h"
#include "RecoJets/JetAlgorithms/interface/HEPTopTaggerWrapperV2.h" 
#include "TMVA/Tools.h"
#include "TMVA/Reader.h"


class TopTagProducer : public edm::stream::EDProducer<> { 
 public:
    explicit TopTagProducer(const edm::ParameterSet& iConfig);
    
    ~TopTagProducer() override {}
    
    void produce(edm::Event & iEvent, const edm::EventSetup & iSetup) override ;
    
 private:	
    edm::InputTag src_;
    edm::EDGetTokenT<edm::View<reco::Jet>> src_token_;

    std::unique_ptr<fastjet::JetDefinition> jetDef{nullptr};
    std::unique_ptr<fastjet::AreaDefinition> areaDef{nullptr};
    std::unique_ptr<fastjet::GhostedAreaSpec> activeArea{nullptr};
    std::unique_ptr<fastjet::contrib::SoftDrop> softDrop{nullptr};

    std::unique_ptr<fastjet::contrib::Njettiness> tauN{nullptr}; 
    std::unique_ptr<ECFCalculator> ecfcalc{nullptr};
    std::unique_ptr<fastjet::HEPTopTaggerV2> htt{nullptr};

    std::map<std::string, std::unique_ptr<TMVA::Reader>> bdts;

    // variables 
    float tau32sd;
    std::vector<float> ecfs;
    float htt_frec, htt_mass;
    float spectator=1;

    float get_ecf(int o, int n, int ib) {
	return std::get<ECFCalculator::ecfP>(ecfcalc->access(ECFCalculator::pos_type(o-1, n-1, ib)));
    }

    void reset() {
	tau32sd = 0;
	htt_frec = 0;
	for (auto& e : ecfs)
	    e = 0;
    }

};

#endif
