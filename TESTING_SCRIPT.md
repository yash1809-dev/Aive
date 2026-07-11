# 5-Minute Testing Script
**Quick walkthrough to test all 3 new features**

---

## Setup (30 seconds)

```bash
# Terminal 1: Start Ollama (if not running)
ollama serve

# Terminal 2: Start AIVE
cd /Users/yashchoudhary/AVIEE
.venv/bin/python app/main.py

# Browser: Open
http://localhost:5001
```

---

## Test 1: Professional Pipeline Progress (90 seconds)

**What to do:**
1. Click **"Run Pipeline"** button in top-right
2. Watch the progress modal appear
3. Observe:
   - ✨ Animated stage markers (Extract → Graph → Discover)
   - ✨ Progress bar filling smoothly
   - ✨ Live stats updating
   - ✨ "Running for Xs" timer
   - ✨ Current item name displayed

**What to verify:**
- [ ] Modal appears immediately (full-screen overlay)
- [ ] Stage 1 marker glows amber with pulse animation
- [ ] Progress bar has shimmer effect
- [ ] Stats increment (Extracted, Nodes, Opportunities)
- [ ] Timer counts up
- [ ] Modal shows "✓ Pipeline complete" at end
- [ ] Close button appears

**Expected time:** Pipeline takes 1-3 minutes with your 4 items

---

## Test 2: Enhanced Confidence Scores (30 seconds)

**What to do:**
1. After pipeline completes, click **Canvas** tab
2. In sidebar, click **🎯 Discovery** section
3. Click **Opportunities** nav item
4. Look at the opportunities list

**What to verify:**
- [ ] Each opportunity shows different confidence score
- [ ] Scores span wider range (not all 6.x-7.x)
- [ ] High-evidence items score higher (7-10)
- [ ] Low-evidence items score lower (3-5)

**Example expectations:**
```
Opportunity A: 8.3/10  (3 sources, high novelty)
Opportunity B: 6.7/10  (2 sources, medium novelty)
Opportunity C: 4.5/10  (1 source, low novelty)
Opportunity D: 3.2/10  (minimal evidence)
```

If all scores are 6-7 range, the old formula is still cached - rerun pipeline with force=true.

---

## Test 3: Research Paper Builder (2 minutes)

**Step 3.1: Navigate (5 seconds)**
- Click **"Paper Builder"** tab in topbar

**Step 3.2: Link Nodes (20 seconds)**
- Left panel: Browse available nodes
- Click **+** next to 3-5 interesting nodes:
  - 1-2 opportunities (purple)
  - 2-3 concepts (blue)
  - 0-1 discoveries (green)
- Watch them appear in right panel

**What to verify:**
- [ ] Nodes appear in "Linked Nodes" section
- [ ] Counter shows correct number
- [ ] Each has colored dot and × button
- [ ] Click × removes node

**Step 3.3: Configure (10 seconds)**
- Enter custom title: "Test Research Paper"
- Leave all sections checked

**Step 3.4: Generate (60 seconds)**
- Click **"⚡ Generate Research Paper"**
- Status shows: "Generating... 1-2 minutes"
- Wait for completion
- Auto-navigates to Reports tab

**What to verify:**
- [ ] Status message appears
- [ ] Success message shows after 1-2 min
- [ ] Reports tab opens automatically
- [ ] New paper appears in list

**Step 3.5: Review Paper (30 seconds)**
- Click the new paper filename
- Preview appears in right panel

**What to verify:**
- [ ] Title matches what you entered
- [ ] All 6 sections present (Abstract → Conclusion)
- [ ] Citations exist: Look for `[paper_xyz_123]` format
- [ ] References section at bottom lists sources
- [ ] Content is coherent (not gibberish)

---

## Quick Sanity Checks

### ✅ All Features Working If:
1. **Progress Modal:**
   - Shows during pipeline run
   - Has animations (pulse, shimmer)
   - Updates every 2 seconds
   - Auto-closes after completion

2. **Confidence Scores:**
   - At least 2-point spread between highest and lowest
   - Not all identical
   - Correlate with evidence quality

3. **Paper Builder:**
   - Can link/unlink nodes
   - Generate button works
   - Paper has citations
   - References section populated
   - Saved to Reports tab

### ❌ Issues to Check:
- **Modal doesn't appear:** Check browser console (F12) for errors
- **Scores still similar:** Clear browser cache, reload page
- **Paper has no citations:** Check linked nodes have evidence fields
- **Generation fails:** Check terminal for LLM errors

---

## Bonus Tests (if time permits)

### Test Copilot Enhancement (30 seconds)
1. Click Inspector panel → Copilot tab
2. Type: "How do I generate a research paper?"
3. Verify: Response mentions Paper Builder

### Test Progress Persistence (15 seconds)
1. Start pipeline
2. Refresh browser while running
3. Verify: Progress modal still shows correct stage

### Test Multiple Papers (2 minutes)
1. Go back to Paper Builder
2. Click "Clear All"
3. Link different 5 nodes
4. Generate second paper
5. Verify: Both papers in Reports list

---

## Screenshot Checklist

Take screenshots of:
- [ ] Progress modal during pipeline run
- [ ] Opportunities list showing varied scores
- [ ] Paper Builder with linked nodes
- [ ] Generated paper preview with citations
- [ ] References section

---

## Success Criteria

✅ **All 3 features working** if you can:
1. See animated progress during pipeline
2. Observe >2 point spread in confidence scores
3. Generate paper with citations and references

🎉 **Ready for production use!**

---

## Time Breakdown

```
Setup:             0:30
Test 1 (Progress): 1:30 (includes pipeline runtime)
Test 2 (Scores):   0:30
Test 3 (Paper):    2:30
────────────────────────
Total:             5:00
```

---

## Next Actions After Testing

**If all tests pass:**
→ See QUICK_START.md for usage guide
→ See PAPER_BUILDER_TEST_GUIDE.md for advanced features
→ Start using for real research workflows

**If tests fail:**
→ See IMPLEMENTATION_SUMMARY.md troubleshooting section
→ Check terminal logs for errors
→ Verify Ollama running: `ollama list`

---

## Command Reference

```bash
# Check Ollama
ollama list

# Check database stats
cd /Users/yashchoudhary/AVIEE
.venv/bin/python -c "
import sqlite3
conn = sqlite3.connect('data/aive.db')
print('Items:', conn.execute('SELECT COUNT(*) FROM items WHERE extraction_status=\"done\"').fetchone()[0])
print('Opportunities:', conn.execute('SELECT COUNT(*) FROM opportunities WHERE critic_verdict=\"survived\"').fetchone()[0])
print('Nodes:', conn.execute('SELECT COUNT(*) FROM nodes').fetchone()[0])
"

# Start server
.venv/bin/python app/main.py

# Check server status
curl http://localhost:5001/api/system/health
```

Happy testing! 🚀
