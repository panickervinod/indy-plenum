from functools import partial

import pytest
from plenum.test.malicious_behaviors_node import makeNodeFaulty, \
    delaysPrePrepareProcessing
from stp_core.common.util import adict
from stp_core.common.log import getlogger

from plenum.test.test_node import TestNodeSet

nodeCount = 7
faultyNodes = 2
whitelist = ['cannot process incoming PREPARE']

logger = getlogger()


@pytest.fixture(scope="module")
def setup(startedNodes):
    G = startedNodes.Gamma
    Z = startedNodes.Zeta
    for node in G, Z:
        makeNodeFaulty(node,
                       partial(delaysPrePrepareProcessing, delay=60))
        # Delaying nomination to avoid becoming primary
        # node.delaySelfNomination(10)
    return adict(faulties=(G, Z))


@pytest.fixture(scope="module")
def afterElection(setup, up):
    for n in setup.faulties:
        for r in n.replicas:
            assert not r.isPrimary


def testNumOfSufficientPrepare(afterElection, prepared1, nodeSet: TestNodeSet):
    for n in nodeSet:
        for r in n.replicas:
            if r.isPrimary:
                logger.info("{} is primary".format(r))
