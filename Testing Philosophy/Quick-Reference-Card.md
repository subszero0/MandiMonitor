# Testing Quick Reference Card

> **Keep this handy during development**

## 🚦 **The Five Testing Levels**

1. **Unit Tests** ✅ *Test functions in isolation*
2. **Integration Tests** ✅ *Test components together*  
3. **Simulation Tests** 🆕 *Test real-world scenarios*
4. **Manager Demo Tests** 🎯 *Zero-tolerance validation*
5. **Manual Testing** 🚨 *Reality validation (CRITICAL)*

## ⚡ **Quick Checklist for Any Feature**

```
□ Unit test with clean data
□ Integration test with realistic data
□ Test with broken/missing data
□ Test async context compatibility
□ Test failure scenarios
□ Test concurrent access
□ Manager demo scenario
□ Manual testing with production data patterns
```

## 🔥 **Critical Questions to Ask**

- What happens if the API is down?
- What if the database is full?
- What if users input malicious data?
- What if everything fails at once?
- Would I be embarrassed to demo this?

## 🎯 **Success Metrics**

- ✅ **95%+ success rate** under load
- ✅ **Sub-1000ms response times**
- ✅ **Zero crashes** during failures
- ✅ **Graceful error messages**

## 🚨 **Red Flags**

- ❌ "It works on my machine"
- ❌ Only testing happy paths
- ❌ Perfect test data only
- ❌ No failure scenario tests
- ❌ Performance as afterthought

## 💎 **Golden Rules**

1. **"If it can fail in production, it should fail in testing first"**
2. **"Test with data that looks like production, not like your dreams"**
3. **"Perfect mocks create dangerous false confidence"**
4. **"Manual testing reveals what automated testing misses"**
5. **"If you'd be embarrassed to show this to your boss, fix it"**

## 🛠️ **Common Test Patterns**

### **Type Safety Test**
```python
def test_handles_mixed_types():
    products = [
        {"price": 50000},      # int
        {"price": "N/A"},      # string
        {"price": None}        # None
    ]
    result = filter_products(products, 60000)
    assert result is not None  # Should not crash
```

### **Failure Recovery Test**
```python
async def test_api_failure_recovery():
    with mock_api_failure():
        result = await search_products("test")
        # Should return graceful fallback, not crash
        assert result is not None
```

### **Concurrent Access Test**
```python
async def test_concurrent_users():
    tasks = [simulate_user(i) for i in range(50)]
    results = await asyncio.gather(*tasks)
    failures = [r for r in results if "FAILED" in str(r)]
    assert len(failures) == 0
```

---
**Keep this card visible while coding!**
