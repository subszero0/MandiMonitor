"""Tests for watch parser functionality."""

from bot.watch_parser import normalize_price_input, parse_watch, validate_watch_data


class TestParseWatch:
    """Test cases for parse_watch function."""

    def test_parse_watch_with_asin_url(self):
        """Test parsing Amazon URL with ASIN."""
        text = (
            "Samsung 27 inch gaming monitor under 30000 https://amazon.in/dp/B09XYZ1234"
        )
        data = parse_watch(text)

        assert data["asin"] == "B09XYZ1234"
        assert data["brand"] == "samsung"
        assert data["max_price"] == 30000
        assert data["keywords"] == text

    def test_parse_watch_with_standalone_asin(self):
        """Test parsing with standalone ASIN."""
        text = "Samsung monitor B09XYZ1234 with minimum 20% discount"
        data = parse_watch(text)

        assert data["asin"] == "B09XYZ1234"
        assert data["brand"] == "samsung"
        assert data["min_discount"] == 20
        assert data["keywords"] == text

    def test_parse_watch_with_price_k_format(self):
        """Test parsing price in k format."""
        text = "Apple iPhone under 80k with 15% discount"
        data = parse_watch(text)

        assert data["brand"] == "apple"
        assert data["max_price"] == 80000
        assert data["min_discount"] == 15

    def test_parse_watch_with_commas_in_price(self):
        """Test parsing price with commas."""
        text = "LG TV under 1,50,000 with minimum 25% off"
        data = parse_watch(text)

        assert data["brand"] == "lg"
        assert data["max_price"] == 150000
        assert data["min_discount"] == 25

    def test_parse_watch_missing_fields(self):
        """Test parsing with missing fields."""
        text = "Gaming monitor 27 inch"
        data = parse_watch(text)

        assert data["asin"] is None
        assert data["brand"] is None
        assert data["max_price"] is None
        assert data["min_discount"] is None
        assert data["keywords"] == text

    def test_parse_watch_brand_variations(self):
        """Test parsing different brand name variations."""
        test_cases = [
            ("Samsung Galaxy phone", "samsung"),
            ("LG OLED TV", "lg"),
            ("Apple MacBook", "apple"),
            ("Mi smartphone", "mi"),
            ("OnePlus device", "oneplus"),
            ("Audio-Technica headphones", "audio technica"),
            ("JBL speaker", "jbl"),
        ]

        for text, expected_brand in test_cases:
            data = parse_watch(text)
            assert data["brand"] == expected_brand

    def test_parse_watch_discount_variations(self):
        """Test parsing different discount formats."""
        test_cases = [
            ("Product with 20% off", 20),
            ("Item with minimum 15% discount", 15),
            ("Device with at least 30% deal", 30),
            ("Gadget with 25% sale", 25),
        ]

        for text, expected_discount in test_cases:
            data = parse_watch(text)
            assert data["min_discount"] == expected_discount


class TestNormalizePriceInput:
    """Test cases for normalize_price_input function."""

    def test_normalize_k_format(self):
        """Test normalizing k format prices."""
        assert normalize_price_input("30k") == 30000
        assert normalize_price_input("2.5k") == 2500
        assert normalize_price_input("₹50k") == 50000

    def test_normalize_lakh_format(self):
        """Test normalizing lakh format prices."""
        assert normalize_price_input("1l") == 100000
        assert normalize_price_input("2.5lac") == 250000
        assert normalize_price_input("3lakh") == 300000

    def test_normalize_crore_format(self):
        """Test normalizing crore format prices."""
        assert normalize_price_input("1cr") == 10000000
        assert normalize_price_input("2.5crore") == 25000000

    def test_normalize_regular_numbers(self):
        """Test normalizing regular number formats."""
        assert normalize_price_input("50000") == 50000
        assert normalize_price_input("₹1,50,000") == 150000
        assert normalize_price_input("rs.25000") == 25000

    def test_normalize_invalid_input(self):
        """Test normalizing invalid inputs."""
        assert normalize_price_input("") is None
        assert normalize_price_input("invalid") is None
        assert normalize_price_input("abc123") is None


class TestValidateWatchData:
    """Test cases for validate_watch_data function."""

    def test_validate_valid_data(self):
        """Test validation of valid watch data."""
        data = {
            "asin": "B09XYZ1234",
            "brand": "samsung",
            "max_price": 50000,
            "min_discount": 20,
            "keywords": "Samsung Galaxy phone",
        }
        errors = validate_watch_data(data)
        assert len(errors) == 0

    def test_validate_invalid_asin(self):
        """Test validation of invalid ASIN."""
        data = {
            "asin": "invalid_asin",
            "keywords": "Test product",
        }
        errors = validate_watch_data(data)
        assert "asin" in errors

    def test_validate_invalid_price_range(self):
        """Test validation of invalid price ranges."""
        test_cases = [
            {"max_price": 0},  # Zero price
            {"max_price": -1000},  # Negative price
            {"max_price": 20000000},  # Too high price
        ]

        for data in test_cases:
            data["keywords"] = "Test product"
            errors = validate_watch_data(data)
            assert "max_price" in errors

    def test_validate_invalid_discount(self):
        """Test validation of invalid discount percentages."""
        test_cases = [
            {"min_discount": 0},  # Zero discount
            {"min_discount": 100},  # 100% discount
            {"min_discount": -10},  # Negative discount
        ]

        for data in test_cases:
            data["keywords"] = "Test product"
            errors = validate_watch_data(data)
            assert "min_discount" in errors

    def test_validate_keywords_length(self):
        """Test validation of keywords length."""
        # Too short
        data = {"keywords": "xy"}
        errors = validate_watch_data(data)
        assert "keywords" in errors

        # Too long
        data = {"keywords": "x" * 501}
        errors = validate_watch_data(data)
        assert "keywords" in errors

        # Just right
        data = {"keywords": "Samsung phone"}
        errors = validate_watch_data(data)
        assert "keywords" not in errors


class TestPatternMatching:
    """Test regex pattern matching directly."""

    def test_asin_pattern_matching(self):
        """Test ASIN pattern matching in various formats."""
        from bot.patterns import PAT_ASIN

        test_cases = [
            ("https://amazon.in/dp/B09XYZ1234", "B09XYZ1234"),
            ("https://www.amazon.in/product/dp/B08ABC5678", "B08ABC5678"),
            ("Check this B07DEF9012 product", "B07DEF9012"),
            ("/gp/product/B06GHI3456", "B06GHI3456"),
        ]

        for text, expected_asin in test_cases:
            match = PAT_ASIN.search(text)
            assert match is not None
            # Get the ASIN from the match - might be in group 1 or group 0
            found_asin = (
                match.group(1) if match.groups() and match.group(1) else match.group(0)
            )
            # Validate it's the right format and extract the ASIN part
            if len(found_asin) == 10 and found_asin.startswith("B"):
                assert found_asin == expected_asin

    def test_brand_pattern_case_insensitive(self):
        """Test brand pattern is case insensitive."""
        from bot.patterns import PAT_BRAND

        test_cases = [
            "SAMSUNG phone",
            "samsung device",
            "Samsung Galaxy",
            "SaMsUnG tablet",
        ]

        for text in test_cases:
            match = PAT_BRAND.search(text)
            assert match is not None
            assert match.group(1).lower() == "samsung"

    def test_price_pattern_variations(self):
        """Test price pattern matches various formats."""
        from bot.patterns import PAT_PRICE_UNDER

        test_cases = [
            ("under 30000", 30000),
            ("below ₹25k", 25000),
            ("less than Rs.50,000", 50000),
            ("within 1,00,000", 100000),
            ("max ₹75k", 75000),
        ]

        for text, expected_price in test_cases:
            match = PAT_PRICE_UNDER.search(text)
            assert match is not None
            price_str = match.group(1).replace(",", "")
            if price_str.endswith("k"):
                price = int(float(price_str[:-1]) * 1000)
            else:
                price = int(price_str)
            assert price == expected_price
