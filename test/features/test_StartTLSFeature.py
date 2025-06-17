from pyjabber.features.StartTLSFeature import StartTLSFeature, proceed_response


def test_initialization_required():
    starttls_feature = StartTLSFeature()
    assert starttls_feature.tag == "starttls"
    assert starttls_feature.attrib == {"xmlns": "urn:ietf:params:xml:ns:xmpp-tls"}
    assert len(starttls_feature) == 1
    assert starttls_feature[0].tag == "required"


def test_initialization_not_required():
    starttls_feature = StartTLSFeature(required=False)
    assert starttls_feature.tag == "starttls"
    assert starttls_feature.attrib == {"xmlns": "urn:ietf:params:xml:ns:xmpp-tls"}
    assert len(starttls_feature) == 0


def test_proceed_response():
    response = proceed_response()
    expected_response = b'<proceed xmlns="urn:ietf:params:xml:ns:xmpp-tls" />'
    assert response == expected_response
