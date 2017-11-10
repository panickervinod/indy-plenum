import pytest

from plenum.common.constants import ROOT_HASH, MULTI_SIGNATURE, PROOF_NODES, TXN_TYPE, DATA, TXN_TIME, STATE_PROOF, \
    MULTI_SIGNATURE_VALUE, MULTI_SIGNATURE_PARTICIPANTS, MULTI_SIGNATURE_SIGNATURE, MULTI_SIGNATURE_VALUE_LEDGER_ID, \
    MULTI_SIGNATURE_VALUE_STATE_ROOT, MULTI_SIGNATURE_VALUE_TXN_ROOT, MULTI_SIGNATURE_VALUE_POOL_STATE_ROOT, \
    MULTI_SIGNATURE_VALUE_TIMESTAMP
from plenum.common.plenum_protocol_version import PlenumProtocolVersion
from plenum.common.request import SafeRequest
from plenum.common.types import f
from plenum.server.domain_req_handler import DomainRequestHandler
from plenum.test.helper import sendRandomRequests, wait_for_requests_ordered, \
    randomOperation
from plenum.test.pool_transactions.conftest import looper, clientAndWallet1, \
    client1, wallet1, client1Connected

nodeCount = 4
nodes_wth_bls = 4


@pytest.fixture(scope='module')
def send_request(looper, txnPoolNodeSet,
                 client1, client1Connected, wallet1):
    reqs = sendRandomRequests(wallet1, client1, 1)
    wait_for_requests_ordered(looper, txnPoolNodeSet, reqs)
    return reqs[0]


def check_read_result(txnPoolNodeSet, request, client, should_have_proof):
    for node in txnPoolNodeSet:
        key = node.reqHandler.prepare_buy_key(request.identifier)
        data = DomainRequestHandler.stateSerializer.deserialize(
            node.reqHandler.state.get(key))

        proof = node.reqHandler.make_proof(key)
        result = node.reqHandler.make_read_result(request,
                                                  data,
                                                  data[f.SEQ_NO.nm],
                                                  data[TXN_TIME],
                                                  proof)
        assert result
        assert result[DATA] == data
        assert result[f.IDENTIFIER.nm] == request.identifier
        assert result[f.REQ_ID.nm] == request.reqId
        assert result[f.SEQ_NO.nm] == data[f.SEQ_NO.nm]
        assert result[TXN_TIME] == data[TXN_TIME]

        if should_have_proof:
            assert result[STATE_PROOF] == proof
            assert client.validate_proof(result)
        else:
            assert STATE_PROOF not in result


def check_write_result(txnPoolNodeSet, req, client, should_have_proof):
    for node in txnPoolNodeSet:
        key = node.reqHandler.prepare_buy_key(req.identifier)
        txn = DomainRequestHandler.stateSerializer.deserialize(
            node.reqHandler.state.get(key))

        path = node.reqHandler.get_path_for_txn(txn)
        proof = node.reqHandler.make_proof(path) if path else None
        result = node.reqHandler.make_write_result(
            request=req, txn=txn, proof=proof)

        assert result
        assert result[TXN_TYPE] == txn[TXN_TYPE]
        assert result["amount"] == txn["amount"]

        if should_have_proof:
            assert result[STATE_PROOF]
            assert client.validate_proof(result)
        else:
            assert STATE_PROOF not in result


def test_make_proof_bls_enabled(send_request,
                                txnPoolNodeSet, client1):
    req = send_request
    for node in txnPoolNodeSet:
        key = node.reqHandler.prepare_buy_key(req.identifier)
        proof = node.reqHandler.make_proof(key)

        assert proof
        assert ROOT_HASH in proof
        assert MULTI_SIGNATURE in proof
        assert PROOF_NODES in proof

        multi_sig = proof[MULTI_SIGNATURE]
        assert MULTI_SIGNATURE_SIGNATURE in multi_sig
        assert MULTI_SIGNATURE_PARTICIPANTS in multi_sig
        assert MULTI_SIGNATURE_VALUE in multi_sig

        multi_sig_value = multi_sig[MULTI_SIGNATURE_VALUE]
        assert MULTI_SIGNATURE_VALUE_LEDGER_ID in multi_sig_value
        assert MULTI_SIGNATURE_VALUE_STATE_ROOT in multi_sig_value
        assert MULTI_SIGNATURE_VALUE_TXN_ROOT in multi_sig_value
        assert MULTI_SIGNATURE_VALUE_POOL_STATE_ROOT in multi_sig_value
        assert MULTI_SIGNATURE_VALUE_TIMESTAMP in multi_sig_value
        # check that multi sig values are in order
        value_keys = list(multi_sig_value.keys())
        assert [MULTI_SIGNATURE_VALUE_LEDGER_ID, MULTI_SIGNATURE_VALUE_POOL_STATE_ROOT,
                MULTI_SIGNATURE_VALUE_STATE_ROOT, MULTI_SIGNATURE_VALUE_TIMESTAMP,
                MULTI_SIGNATURE_VALUE_TXN_ROOT] == value_keys

        assert client1.validate_multi_signature(proof)


def test_make_read_result_bls_enabled(send_request,
                                      txnPoolNodeSet, client1):
    req = send_request
    assert req.protocolVersion
    assert req.protocolVersion >= PlenumProtocolVersion.STATE_PROOF_SUPPORT.value

    request = SafeRequest(identifier=req.identifier,
                          reqId=100,
                          operation={TXN_TYPE: "get_buy"},
                          signature="signature",
                          protocolVersion=PlenumProtocolVersion.STATE_PROOF_SUPPORT.value)
    check_read_result(txnPoolNodeSet, request, client1, True)


def test_make_write_result_bls_enabled(send_request,
                                       txnPoolNodeSet, client1):
    req = send_request
    assert req.protocolVersion
    assert req.protocolVersion >= PlenumProtocolVersion.STATE_PROOF_SUPPORT.value

    check_write_result(txnPoolNodeSet, req, client1, True)


def test_make_read_result_no_protocol_version(send_request,
                                              txnPoolNodeSet, client1):
    req = send_request
    request = SafeRequest(identifier=req.identifier,
                          reqId=1,
                          operation={TXN_TYPE: "get_buy"},
                          signature="signature")
    request.protocolVersion = False
    check_read_result(txnPoolNodeSet, request, client1, False)


def test_make_write_result_no_protocol_version(send_request,
                                               txnPoolNodeSet, client1):
    req = send_request
    request = SafeRequest(identifier=req.identifier,
                          reqId=1,
                          operation=randomOperation(),
                          signature="signature")
    request.protocolVersion = False
    check_write_result(txnPoolNodeSet, request, client1, False)


def test_make_read_result_protocol_version_less_than_state_proof(send_request,
                                                                 txnPoolNodeSet, client1):
    req = send_request
    request = SafeRequest(identifier=req.identifier,
                          reqId=1,
                          operation={TXN_TYPE: "get_buy"},
                          signature="signature")
    request.protocolVersion = 0
    check_read_result(txnPoolNodeSet, request, client1, False)


def test_make_write_result_protocol_version_less_than_state_proof(send_request,
                                                                  txnPoolNodeSet, client1):
    req = send_request
    request = SafeRequest(identifier=req.identifier,
                          reqId=1,
                          operation=randomOperation(),
                          signature="signature")
    request.protocolVersion = 0
    check_write_result(txnPoolNodeSet, request, client1, False)


def test_make_read_result_no_protocol_version_in_request_by_default(send_request, txnPoolNodeSet):
    req = send_request
    request = SafeRequest(identifier=req.identifier,
                          reqId=1,
                          operation=randomOperation(),
                          signature="signature")
    check_read_result(txnPoolNodeSet, request, client1, False)


def test_make_write_result_no_protocol_version_in_request_by_default(send_request, txnPoolNodeSet):
    req = send_request
    request = SafeRequest(identifier=req.identifier,
                          reqId=1,
                          operation=randomOperation(),
                          signature="signature")
    check_write_result(txnPoolNodeSet, request, client1, False)


def test_proof_in_write_reply(send_request, client1):
    req = send_request
    result = client1.getReply(req.identifier, req.reqId)[0]

    assert result
    assert result[TXN_TYPE] == "buy"
    assert result[f.IDENTIFIER.nm] == req.identifier
    assert result[f.REQ_ID.nm] == req.reqId
    assert result[f.SEQ_NO.nm]
    assert result[TXN_TIME]
    assert STATE_PROOF in result

    state_proof = result[STATE_PROOF]
    assert ROOT_HASH in state_proof
    assert MULTI_SIGNATURE in state_proof
    assert PROOF_NODES in state_proof

    multi_sig = state_proof[MULTI_SIGNATURE]
    assert MULTI_SIGNATURE_SIGNATURE in multi_sig
    assert MULTI_SIGNATURE_PARTICIPANTS in multi_sig
    assert MULTI_SIGNATURE_VALUE in multi_sig

    multi_sig_value = multi_sig[MULTI_SIGNATURE_VALUE]
    assert MULTI_SIGNATURE_VALUE_LEDGER_ID in multi_sig_value
    assert MULTI_SIGNATURE_VALUE_STATE_ROOT in multi_sig_value
    assert MULTI_SIGNATURE_VALUE_TXN_ROOT in multi_sig_value
    assert MULTI_SIGNATURE_VALUE_POOL_STATE_ROOT in multi_sig_value
    assert MULTI_SIGNATURE_VALUE_TIMESTAMP in multi_sig_value

    assert client1.validate_multi_signature(state_proof)
    assert client1.validate_proof(result)
