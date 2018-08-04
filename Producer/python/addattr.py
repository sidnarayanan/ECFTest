import FWCore.ParameterSet.Config as cms

class AddAttr(object):
    def __init__(self, process, sequence, postfix = ''):
        self.process = process
        self.sequence = sequence
        self.postfix = postfix
        self.last = None

    def __call__(self, name, attr):
        if hasattr(self.process, name + self.postfix):
            raise RuntimeError('process already has an attribute named ' + name + self.postfix)

        setattr(self.process, name + self.postfix, attr)
        self.sequence += attr

        self.last = attr

        return cms.InputTag(name + self.postfix)
