# Discovery Documentation Template

> **Use this template to document new testing insights from each project**

## **Project**: [Project Name]
**Date**: [YYYY-MM-DD]  
**Team Members**: [Names]  
**Technology Stack**: [Languages/Frameworks]

---

## 🎯 **Challenge Faced**

**Context**: [What were you building/fixing?]

**Problem**: [What issue did you encounter?]

**Initial Symptoms**: [How did the problem manifest?]

---

## 🔍 **Discovery Process**

**What Testing Revealed**:
- [What your tests found]
- [Which testing level caught it]
- [Why it wasn't caught earlier]

**Investigation Steps**:
1. [First thing you tried]
2. [Second approach]
3. [Final breakthrough]

**Root Cause**: [The actual underlying issue]

---

## 🔧 **Solution**

**The Fix**:
```code
// Before (broken):
[paste broken code]

// After (fixed):
[paste fixed code]
```

**Why This Works**: [Explanation of the fix]

**Alternative Solutions Considered**:
- [Option 1] - Why not chosen
- [Option 2] - Why not chosen

---

## 📚 **Learning Extracted**

**General Principle**: [What rule/principle can be extracted?]

**Testing Strategy**: [What testing approach would catch this in future?]

**Code Pattern**: [Any coding pattern that prevents this?]

**Team Process**: [Any process change needed?]

---

## 🚀 **Application for Future Projects**

**Immediate Actions**:
- [ ] [Action item 1]
- [ ] [Action item 2]
- [ ] [Action item 3]

**Testing Checklist Addition**:
```
□ [New test type to add to standard checklist]
□ [Another preventive test]
```

**Code Review Focus**:
- [What to look for in code reviews]
- [Red flags to watch for]

---

## 📊 **Impact Assessment**

**Before Fix**:
- Success Rate: [X%]
- Performance: [metrics]
- User Experience: [description]

**After Fix**:
- Success Rate: [Y%]
- Performance: [metrics]
- User Experience: [description]

**Business Impact**: [How this affected/could have affected the business]

---

## 🧪 **Test Cases Added**

### **Unit Tests**
```python
def test_[specific_scenario]():
    # Test that prevents this specific issue
    pass
```

### **Integration Tests**
```python
async def test_[integration_scenario]():
    # Test that catches this at system level
    pass
```

### **Simulation Tests**
```python
async def test_[realistic_scenario]():
    # Test that catches this under realistic conditions
    pass
```

---

## 🔮 **Future Considerations**

**Similar Issues to Watch For**:
- [Related issue 1]
- [Related issue 2]

**Technology Debt Created**:
- [Any shortcuts taken]
- [Technical debt to address later]

**Monitoring/Alerting Added**:
- [New metrics to track]
- [Alerts to set up]

---

## 📝 **Team Knowledge Sharing**

**Shared With**:
- [ ] Team meeting presentation
- [ ] Documentation update
- [ ] Code review guidelines update
- [ ] Testing philosophy update

**Knowledge Base Updates**:
- [ ] Wiki/Confluence page
- [ ] README updates
- [ ] Onboarding materials

---

## 🏷️ **Tags for Future Reference**

`#[technology-name]` `#[issue-type]` `#[testing-level]` `#[severity]`

Examples: `#python` `#async` `#integration-testing` `#critical`

---

**Reviewed By**: [Team lead/senior developer]  
**Approved**: [Date]  
**Next Review**: [Date for follow-up]
