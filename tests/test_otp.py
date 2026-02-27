from api.services.otp import generate_otp, verify_otp


def test_otp_generate_and_verify():
    key = "order:test"
    code = generate_otp(key)
    assert len(code) == 6
    assert code.isdigit()
    assert verify_otp(key, code) is True
    # second verify should fail (one-time)
    assert verify_otp(key, code) is False

