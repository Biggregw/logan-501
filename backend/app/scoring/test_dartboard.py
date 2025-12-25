from app.scoring.dartboard import DartboardCalibration, score_dart_pixel


def test_dbull() -> None:
    calib = DartboardCalibration(center_x=0, center_y=0, radius_px=100, rotation_deg=0)
    d = score_dart_pixel(x=1.0, y=1.0, calib=calib)
    assert (d.value, d.multiplier, d.score, d.ring) == (25, 2, 50, "dbull")


def test_bull() -> None:
    calib = DartboardCalibration(center_x=0, center_y=0, radius_px=100, rotation_deg=0)
    d = score_dart_pixel(x=0.0, y=8.0, calib=calib)  # 0.08R -> outer bull
    assert (d.value, d.multiplier, d.score, d.ring) == (25, 1, 25, "bull")


def test_double_20_top() -> None:
    calib = DartboardCalibration(center_x=0, center_y=0, radius_px=100, rotation_deg=0)
    d = score_dart_pixel(x=0.0, y=-98.0, calib=calib)  # top, double ring
    assert (d.value, d.multiplier, d.score, d.ring) == (20, 2, 40, "double")


def test_double_6_right() -> None:
    calib = DartboardCalibration(center_x=0, center_y=0, radius_px=100, rotation_deg=0)
    d = score_dart_pixel(x=98.0, y=0.0, calib=calib)  # right, double ring
    assert (d.value, d.multiplier, d.score, d.ring) == (6, 2, 12, "double")


def test_triple_20_top() -> None:
    calib = DartboardCalibration(center_x=0, center_y=0, radius_px=100, rotation_deg=0)
    d = score_dart_pixel(x=0.0, y=-60.0, calib=calib)  # top, triple ring (0.60R)
    assert (d.value, d.multiplier, d.score, d.ring) == (20, 3, 60, "triple")


def test_miss_outside_board() -> None:
    calib = DartboardCalibration(center_x=0, center_y=0, radius_px=100, rotation_deg=0)
    d = score_dart_pixel(x=0.0, y=-120.0, calib=calib)
    assert (d.value, d.multiplier, d.score, d.ring) == (0, 0, 0, "miss")


def test_rotation_changes_sector_mapping() -> None:
    # With a +90° clockwise rotation, "top" should map to what used to be at +90° (right),
    # which is sector 6 on a standard board.
    calib = DartboardCalibration(center_x=0, center_y=0, radius_px=100, rotation_deg=90)
    d = score_dart_pixel(x=0.0, y=-98.0, calib=calib)
    assert d.value == 6

