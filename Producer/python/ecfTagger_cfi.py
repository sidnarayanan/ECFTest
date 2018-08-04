import FWCore.ParameterSet.Config as cms

ecfTagger = cms.EDProducer("TopTagProducer",
                            src=cms.InputTag("pfJetsCA15PFPuppi"))
