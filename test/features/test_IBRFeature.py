from pyjabber.features.InBandRegistration import InBandRegistration


def test_ibr_class():
    ibr_element = InBandRegistration()
    assert ibr_element is not None
    assert ibr_element.tag == "{http://jabber.org/features/iq-register}register"
