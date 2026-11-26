from scanner.tags import LABELS, assign_tag


def test_anomaly_tags_use_the_contract_labels():
    down = assign_tag(True, "down")
    up = assign_tag(True, "up")
    sideways = assign_tag(True, "sideways")
    assert down == {
        "bargaining_power": "buyer_absorption",
        "bargaining_power_label_en": "Buyer Absorption",
        "bargaining_power_label_zh": "買方暗中承接",
    }
    assert up == {
        "bargaining_power": "seller_distribution",
        "bargaining_power_label_en": "Seller Distribution",
        "bargaining_power_label_zh": "賣方暗中出貨",
    }
    assert sideways == {
        "bargaining_power": "stalemate_compression",
        "bargaining_power_label_en": "Stalemate / Compression",
        "bargaining_power_label_zh": "多空角力壓縮",
    }
    assert (down["bargaining_power_label_en"], down["bargaining_power_label_zh"]) == LABELS["buyer_absorption"]


def test_non_anomaly_tags_are_null():
    assert assign_tag(False, "down") == {
        "bargaining_power": None,
        "bargaining_power_label_en": None,
        "bargaining_power_label_zh": None,
    }
    assert assign_tag(False, "up")["bargaining_power"] is None
    assert assign_tag(False, "sideways")["bargaining_power_label_zh"] is None
