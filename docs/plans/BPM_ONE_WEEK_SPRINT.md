# BPM Automation - ONE WEEK SPRINT PLAN 🚀
**Duration:** 7 days (168 hours)
**Team Leader:** Opus 4.6 (YOU)
**Agents:** 6x Sonnet 4.5 (parallel execution)
**Status:** READY TO LAUNCH

---

## ⚡ SPRINT PHILOSOPHY

**"MVP or Die"** - Build the minimum viable product that delivers REAL VALUE.

### What We're Building (MVP Scope)
✅ **Core workflow execution** - Linear workflows with actions
✅ **Basic triggers** - Record create/write, manual, scheduled
✅ **Essential actions** - Update/create records, send email, create activity
✅ **Human tasks** - Basic approval workflow
✅ **Simple monitoring** - Dashboard, logs, instance tracking
✅ **Basic API** - Trigger workflows via API

### What We're NOT Building (Phase 2)
❌ Parallel execution (too complex for Week 1)
❌ Webhooks (nice-to-have)
❌ Advanced executors (wait_event, delay)
❌ Escalation (basic tasks only)
❌ Fancy UI (functional > pretty)
❌ 18 action executors (start with 8)

### Success Definition (ONE WEEK)
- [ ] **Workflow:** Can create a workflow via UI
- [ ] **Trigger:** Workflow fires when record created
- [ ] **Execute:** Actions execute (update record, send email)
- [ ] **Tasks:** Human task created and can be approved
- [ ] **Monitor:** Dashboard shows running workflows
- [ ] **Test:** Core paths have tests (60%+ coverage)
- [ ] **Demo:** Working end-to-end demo workflow

---

## 📅 7-DAY TIMELINE (AGGRESSIVE)

### **DAY 1: FOUNDATION BLITZ** ⚡
**Goal:** Module structure + Core models operational
**Team:** All 6 agents working in parallel

#### Morning (Hours 0-6)
**Agent 1 - Foundation:** Module structure, security, menus
**Agent 2 - Core Models:** bpm.workflow, bpm.workflow.step (5 models)
**Agent 3 - Execution Models:** bpm.workflow.instance, bpm.instance.step.log, bpm.outbox (3 models)
**Agent 4 - Action Models:** bpm.action, bpm.action.field.map (2 models)
**Agent 5 - Trigger Models:** bpm.trigger (1 model)
**Agent 6 - Task Models:** bpm.task, bpm.execution.log (2 models)

**Deliverables (6 hours):**
- ✅ Module installable
- ✅ 13 core models created (simplified, no complex fields yet)
- ✅ Security groups defined
- ✅ Basic menu structure

#### Afternoon (Hours 6-12)
**Team:** All agents refining their models
- Add computed fields
- Add constraints
- Add basic methods
- Add minimal views (tree/form)

**Deliverables (12 hours total):**
- ✅ 13 models fully functional
- ✅ Can create workflow via UI
- ✅ Can create steps via UI
- ✅ Can create triggers via UI
- ✅ Basic CRUD working

**YOU (Team Leader):**
- Review model definitions (rolling review)
- Merge completed work
- Unblock agents
- Integration testing

---

### **DAY 2: TRIGGER ENGINE + ORCHESTRATOR** ⚡
**Goal:** Workflows can be triggered and queued

#### Morning (Hours 12-18)
**Agent 1 - Trigger Engine Core:**
- `engine/trigger_engine.py`
- Implement on_record_create, on_record_write
- Implement fire_manual, fire_scheduled
- Cache management

**Agent 2 - ORM Mixin:**
- `models/bpm_trigger_mixin.py`
- Override create/write
- Integrate with trigger engine

**Agent 3 - Orchestrator Core:**
- `engine/orchestrator.py`
- process_outbox() basic version (no locking yet)
- _acquire_items(), _process_item()

**Agent 4 - Base Executor:**
- `engine/executors/base.py`
- _safe_eval(), _render_jinja()
- Base execute() interface

**Agent 5 - Basic Views:**
- Workflow form view (editable step tree)
- Instance tree/form views
- Task kanban view

**Agent 6 - Testing Framework:**
- Test infrastructure setup
- Basic model tests
- Trigger test skeleton

**Deliverables (18 hours total):**
- ✅ Trigger engine fires on record create
- ✅ Workflow instance created
- ✅ First step added to outbox
- ✅ Orchestrator can pick up items from outbox

#### Afternoon (Hours 18-24)
**ALL AGENTS - Integration:**
- Connect trigger → instance → outbox → orchestrator
- End-to-end test: Create record → Workflow starts → Outbox item created

**YOU (Team Leader):**
- Integration testing
- Fix blocking issues
- Review & merge

**Deliverables (24 hours / END OF DAY 2):**
- ✅ **MILESTONE 1:** Workflows can be triggered!
- ✅ Can create sale.order → Workflow fires → Instance created

---

### **DAY 3: EXECUTORS + ACTIONS** ⚡
**Goal:** Actions execute, workflows complete

#### Morning (Hours 24-30)
**Agent 1 - Step Executors:**
- `engine/executors/action.py` - Execute action via action engine
- `engine/executors/condition.py` - Evaluate condition
- `engine/executors/stop.py` - Stop workflow

**Agent 2 - Action Engine:**
- `engine/action_engine.py`
- Executor dispatch

**Agent 3 - Action Executors (Critical 4):**
- `engine/action_executors/base.py`
- `engine/action_executors/update_record.py`
- `engine/action_executors/create_record.py`
- `engine/action_executors/send_email.py`

**Agent 4 - Action Executors (Next 4):**
- `engine/action_executors/send_message.py`
- `engine/action_executors/create_activity.py`
- `engine/action_executors/server_action.py`
- `engine/action_executors/http_request.py` (basic)

**Agent 5 - Field Mapping:**
- Field mapping resolver
- Static/field/expression value types
- Jinja template support

**Agent 6 - Tests:**
- Executor tests
- Action executor tests
- Integration tests

**Deliverables (30 hours total):**
- ✅ 3 step executors working
- ✅ 8 action executors working
- ✅ Field mappings resolve correctly

#### Afternoon (Hours 30-36)
**ALL AGENTS - Integration:**
- Complete workflow execution: Trigger → Execute → Complete
- Test: Update record action works
- Test: Send email action works
- Test: Condition gateway works

**YOU (Team Leader):**
- Integration testing
- Fix issues
- Performance check

**Deliverables (36 hours / END OF DAY 3):**
- ✅ **MILESTONE 2:** Workflows execute and complete!
- ✅ End-to-end: Trigger → Action → Update record → Complete

---

### **DAY 4: HUMAN TASKS + RETRY LOGIC** ⚡
**Goal:** Approval workflows + Error handling

#### Morning (Hours 36-42)
**Agent 1 - Human Task Executor:**
- `engine/executors/human_task.py`
- Create task
- Resolve assignee (user/field/expression)

**Agent 2 - Task Methods:**
- action_approve()
- action_reject()
- Resume workflow on completion

**Agent 3 - Retry Logic:**
- Exponential backoff
- _schedule_retry()
- _handle_failure()
- Error step execution

**Agent 4 - Context Management:**
- Context updates propagation
- Context storage in instance
- Context availability in executors

**Agent 5 - UI Polish:**
- Task form view (Approve/Reject buttons)
- Task kanban (My Tasks)
- Workflow form improvements

**Agent 6 - Tests:**
- Human task tests
- Retry logic tests
- Error handling tests

**Deliverables (42 hours total):**
- ✅ Human task step creates tasks
- ✅ Tasks can be approved/rejected
- ✅ Workflow resumes after approval
- ✅ Failed steps retry with backoff

#### Afternoon (Hours 42-48)
**ALL AGENTS - Approval Workflow:**
- Build complete approval workflow
- Test: Sale order approval flow
- Test: Retry on failure

**YOU (Team Leader):**
- Integration testing
- Demo preparation

**Deliverables (48 hours / END OF DAY 4):**
- ✅ **MILESTONE 3:** Approval workflows work!
- ✅ Demo: Sale order → Task → Approve → Email sent

---

### **DAY 5: MONITORING + API** ⚡
**Goal:** Dashboard + REST API

#### Morning (Hours 48-54)
**Agent 1 - Dashboard:**
- Dashboard view with statistics
- Real-time metrics (running, failed, pending)
- Recent instances list
- Failed instances list

**Agent 2 - Instance Views:**
- Instance form view (details, logs)
- Instance tree view (filters)
- Step execution timeline
- Control buttons (cancel, retry)

**Agent 3 - Execution Logs:**
- Log viewer (tree view)
- Log filtering
- Integration with instance form

**Agent 4 - REST API:**
- `controllers/api.py`
- POST /api/bpm/workflows/<code>/start
- GET /api/bpm/instances/<id>
- POST /api/bpm/tasks/<id>/complete

**Agent 5 - Scheduled Triggers:**
- Cron job wrapper
- fire_scheduled() implementation
- Cron data XML

**Agent 6 - Tests:**
- API endpoint tests
- Dashboard tests
- UI interaction tests

**Deliverables (54 hours total):**
- ✅ Dashboard shows workflow statistics
- ✅ Instance details viewable
- ✅ Logs viewable and filterable
- ✅ REST API functional

#### Afternoon (Hours 54-60)
**ALL AGENTS - Integration:**
- Connect all pieces
- Test API triggers
- Test scheduled triggers
- Test monitoring updates

**YOU (Team Leader):**
- API testing
- Dashboard validation

**Deliverables (60 hours / END OF DAY 5):**
- ✅ **MILESTONE 4:** Monitoring + API operational!
- ✅ Can trigger via API
- ✅ Dashboard shows real-time data

---

### **DAY 6: TESTING + POLISH** ⚡
**Goal:** Test coverage + Bug fixes

#### All Day (Hours 60-84)
**Agent 1 - Unit Tests:**
- Model tests (all 13 models)
- Constraint tests
- Method tests
- Target: 60%+ coverage

**Agent 2 - Integration Tests:**
- Complete workflow tests
- Trigger type tests
- Executor tests
- Error handling tests

**Agent 3 - Bug Fixes:**
- Fix issues found in testing
- Performance optimization
- Query optimization

**Agent 4 - Documentation:**
- User guide (getting started)
- Workflow creation guide
- API documentation
- README.md

**Agent 5 - Demo Workflows:**
- Purchase order approval
- Lead assignment
- Invoice notification
- Sample data

**Agent 6 - Security Review:**
- Access rights validation
- SQL injection check
- Expression evaluation security
- Input validation

**Deliverables (84 hours / END OF DAY 6):**
- ✅ **MILESTONE 5:** Test coverage 60%+
- ✅ All critical bugs fixed
- ✅ Documentation complete
- ✅ Demo workflows ready

**YOU (Team Leader):**
- Final integration testing
- Demo rehearsal
- Release notes preparation

---

### **DAY 7: DEPLOYMENT + DEMO** 🎉
**Goal:** Production ready + Live demo

#### Morning (Hours 84-90)
**Agent 1 - Database Optimization:**
- Create indexes
- Optimize queries
- Test performance

**Agent 2 - Deployment Prep:**
- Installation guide
- Migration scripts
- Backup procedures

**Agent 3 - Final Polish:**
- UI improvements
- Error messages
- Help text

**Agent 4 - Demo Preparation:**
- Demo script
- Demo data setup
- Presentation slides

**Agent 5 - Final Testing:**
- Smoke tests
- Load testing (100 instances)
- Cross-browser testing

**Agent 6 - Documentation Review:**
- Final doc review
- Screenshots
- Video walkthrough

**Deliverables (90 hours total):**
- ✅ Production ready
- ✅ Demo prepared
- ✅ Documentation complete

#### Afternoon (Hours 90-96) - DEMO DAY! 🚀
**Team Demo:**
1. **Live Workflow Creation** (15 min)
   - Create purchase order approval workflow
   - Add steps (request → approval → notify)
   - Add trigger (on create)

2. **Live Execution** (15 min)
   - Create purchase order
   - Workflow triggers automatically
   - Task created and assigned
   - Approve task
   - Email sent
   - Workflow completes

3. **Dashboard Tour** (10 min)
   - Show running instances
   - Show logs
   - Show statistics

4. **API Demo** (10 min)
   - Trigger via API
   - Check status via API
   - Complete task via API

5. **Q&A** (10 min)

**Deliverables (96 hours / END OF DAY 7):**
- ✅ **FINAL MILESTONE:** Production deployment!
- ✅ Live demo successful
- ✅ Team celebration 🎉

**YOU (Team Leader):**
- Present demo
- Field questions
- Plan Phase 2 (if needed)

---

## 👥 TEAM ASSIGNMENTS (PARALLEL EXECUTION)

### You (Opus 4.6) - Team Leader
**Role:** Architect, Integrator, Reviewer
**Time Allocation:**
- 30% - Architecture decisions & integration
- 30% - Code review & merging
- 20% - Unblocking agents
- 20% - Testing & validation

**Critical Responsibilities:**
- Make fast decisions (no analysis paralysis)
- Review code every 6 hours (rolling reviews)
- Merge completed work immediately
- Run integration tests continuously
- Adjust priorities based on progress

---

### Agent 1 (Sonnet 4.5) - Foundation & Orchestration
**Primary Focus:** Infrastructure, orchestrator, dashboard
**Days 1-2:** Foundation + Trigger engine core
**Days 3-4:** Orchestrator refinement + Retry logic
**Days 5-6:** Dashboard + Monitoring
**Day 7:** Deployment

**Files Owned:**
- Module structure (Day 1)
- `engine/trigger_engine.py` (Day 2)
- `engine/orchestrator.py` (Day 3-4)
- Dashboard views (Day 5)
- Deployment (Day 7)

---

### Agent 2 (Sonnet 4.5) - Core Models & ORM
**Primary Focus:** Data models, ORM integration
**Days 1-2:** Core models + ORM mixin
**Days 3-4:** Action engine + Task methods
**Days 5-6:** Integration tests + Bug fixes
**Day 7:** Final polish

**Files Owned:**
- `models/bpm_workflow.py` (Day 1)
- `models/bpm_workflow_step.py` (Day 1)
- `models/bpm_trigger_mixin.py` (Day 2)
- `engine/action_engine.py` (Day 3)
- `models/bpm_task.py` methods (Day 4)

---

### Agent 3 (Sonnet 4.5) - Execution & Queue
**Primary Focus:** Orchestrator, outbox, execution flow
**Days 1-2:** Execution models + Orchestrator core
**Days 3-4:** Retry logic + Context management
**Days 5-6:** Bug fixes + Optimization
**Day 7:** Performance tuning

**Files Owned:**
- `models/bpm_workflow_instance.py` (Day 1)
- `models/bpm_outbox.py` (Day 1)
- `engine/orchestrator.py` core (Day 2)
- Retry logic (Day 4)

---

### Agent 4 (Sonnet 4.5) - Executors & Actions
**Primary Focus:** Step executors, action executors
**Days 1-2:** Base executor + Action models
**Days 3-4:** Action executors (8 total)
**Days 5-6:** REST API + Documentation
**Day 7:** API polish

**Files Owned:**
- `models/bpm_action.py` (Day 1)
- `engine/executors/base.py` (Day 2)
- `engine/executors/action.py` (Day 3)
- `engine/action_executors/*.py` (Day 3-4)
- `controllers/api.py` (Day 5)

---

### Agent 5 (Sonnet 4.5) - UI & Views
**Primary Focus:** Views, forms, wizards
**Days 1-2:** Basic views (tree/form)
**Days 3-4:** Workflow designer + Task UI
**Days 5-6:** Demo workflows + Polish
**Day 7:** Final UI polish

**Files Owned:**
- `views/menu.xml` (Day 1)
- `views/bpm_workflow_views.xml` (Day 2)
- `views/bpm_task_views.xml` (Day 4)
- `views/bpm_dashboard_views.xml` (Day 5)
- Demo workflows (Day 6)

---

### Agent 6 (Sonnet 4.5) - Testing & QA
**Primary Focus:** Tests, security, documentation
**Days 1-2:** Test framework + Basic tests
**Days 3-4:** Executor tests + Integration tests
**Days 5-6:** Full test suite + Security review
**Day 7:** Final validation

**Files Owned:**
- `tests/` directory (Day 2)
- All test files (Days 3-6)
- Security review (Day 6)
- Documentation review (Day 7)

---

## 🔄 COORDINATION PROTOCOL

### Communication Rhythm
**Every 6 Hours:** Checkpoint with team leader
- What's done?
- What's blocked?
- What's next?

**Every 12 Hours:** Integration sprint
- All agents stop and integrate
- Run tests
- Fix blocking issues
- Replan if needed

**Every 24 Hours:** Milestone review
- Did we hit the milestone?
- What needs adjustment?
- Reprioritize if needed

### Git Workflow (FAST)
```
main (18.0)
├── feature/day1-foundation (Agent 1)
├── feature/day1-models (Agents 2-6)
├── feature/day2-triggers (Agent 1-2)
├── feature/day2-orchestrator (Agent 3)
├── feature/day3-executors (Agents 1-4)
├── feature/day4-tasks (Agents 1-2)
├── feature/day5-monitoring (Agents 1-3)
├── feature/day5-api (Agent 4)
└── feature/day6-testing (Agent 6)
```

**Merge Strategy:**
- Merge every 6 hours (or sooner if ready)
- No waiting for perfect code
- Fix forward, not backward
- "Done is better than perfect"

---

## 🎯 MVP SCOPE (SIMPLIFIED)

### Models (13 instead of 17)
✅ Keep:
1. bpm.workflow
2. bpm.workflow.step
3. bpm.action
4. bpm.action.field.map
5. bpm.trigger
6. bpm.workflow.instance
7. bpm.instance.step.log
8. bpm.execution.log
9. bpm.task
10. bpm.outbox
11. bpm.config.setting

❌ Skip for Week 1:
- bpm.webhook.endpoint (Phase 2)
- bpm.webhook.call.log (Phase 2)
- bpm.schedule.job (Phase 2)
- bpm.parallel.branch (Phase 2)
- bpm.task.response (Phase 2)
- bpm.action.registry (Phase 2)

### Step Executors (3 instead of 8)
✅ Keep:
1. action - Execute action
2. condition - If/else gateway
3. stop - End workflow

❌ Skip for Week 1:
- parallel_split/join (Phase 2)
- wait_event (Phase 2)
- delay (Phase 2)
- human_task (inline in action executor instead)

### Action Executors (8 instead of 18+)
✅ Keep:
1. update_record
2. create_record
3. send_email
4. send_message
5. create_activity
6. server_action
7. http_request (basic)
8. human_task (special)

❌ Skip for Week 1:
- delete_record (Phase 2)
- link_records (Phase 2)
- send_sms (Phase 2)
- webhook_call (Phase 2)
- execute_python (Phase 2)

### Trigger Types (4 instead of 10+)
✅ Keep:
1. on_create
2. on_write
3. manual (button)
4. scheduled (cron)

❌ Skip for Week 1:
- on_delete (Phase 2)
- on_field_change (Phase 2)
- on_condition (Phase 2)
- deadline (Phase 2)
- webhook (Phase 2)
- api (Phase 2 - but REST API trigger will work)

---

## ✅ SUCCESS CRITERIA (ONE WEEK)

### Must Have (Blocking for release)
- [ ] Can create workflow via UI
- [ ] Workflow triggers on record create
- [ ] Actions execute (update, email, activity)
- [ ] Human tasks work (approve/reject)
- [ ] Workflows complete successfully
- [ ] Dashboard shows instances
- [ ] Logs viewable
- [ ] Can trigger via REST API
- [ ] Test coverage > 60%
- [ ] Zero critical bugs
- [ ] Demo works end-to-end

### Nice to Have (Not blocking)
- [ ] Advanced UI features
- [ ] Extensive error messages
- [ ] Fancy dashboard widgets
- [ ] Complete documentation
- [ ] 80%+ test coverage

### Definitely Phase 2
- Parallel execution
- Webhooks
- Advanced executors
- Escalation
- Field change detection
- Advanced retry strategies

---

## 📊 DAILY METRICS

**Track Every Day:**
- Models completed
- Executors completed
- Tests passing
- Integration status
- Blocking issues

**Dashboard (for team leader):**
```
DAY 1: ████████░░░░░░░░░░░░  40% (Models done)
DAY 2: ████████████░░░░░░░░  60% (Trigger + Orchestrator)
DAY 3: ████████████████░░░░  80% (Executors done)
DAY 4: ██████████████████░░  90% (Tasks + Retry)
DAY 5: ███████████████████░  95% (Monitoring + API)
DAY 6: ████████████████████  98% (Testing + Polish)
DAY 7: ████████████████████ 100% (DONE!)
```

---

## 🚨 RISK MANAGEMENT (1 WEEK)

### Top 3 Risks

**1. Scope Creep**
- **Mitigation:** Ruthless prioritization, say NO to nice-to-haves
- **Owner:** Team Leader (YOU)

**2. Integration Issues**
- **Mitigation:** Integrate every 12 hours, fix immediately
- **Owner:** Team Leader (YOU)

**3. Blocking Bugs**
- **Mitigation:** All agents stop to fix critical bugs
- **Owner:** Agent 6 + Team Leader

---

## 🎉 WHAT SUCCESS LOOKS LIKE (END OF WEEK)

**Friday 5 PM Demo:**

```
👨‍💼 Business User: "Can I automate purchase order approvals?"
👨‍💻 You: "Absolutely! Watch this..."

[Create workflow in 2 minutes]
- Name: "PO Approval"
- Trigger: On purchase.order create
- Step 1: Check amount > $10,000
- Step 2 (if true): Create approval task for manager
- Step 3: On approve → Send email
- Step 4: On approve → Update PO state
- Step 5: Stop

[Save & Activate]

[Create test PO for $15,000]
- Workflow triggers automatically ✅
- Task appears in manager's kanban ✅
- Manager approves ✅
- Email sent ✅
- PO state updated ✅
- Workflow shows as "Done" in dashboard ✅

👨‍💼 Business User: 🤯 "That's incredible!"
```

---

## 📝 NEXT STEPS (RIGHT NOW)

**To start this sprint, I need your approval:**

1. **Confirm scope:** MVP features listed above OK?
2. **Confirm timeline:** 7 days (168 hours) realistic for your agents?
3. **Confirm resources:** 6 Sonnet 4.5 agents available 24/7?

**Once you say GO:**
- I'll create the module structure (30 min)
- I'll spawn Agent 1 for foundation (Hour 0)
- I'll spawn Agents 2-6 for models (Hour 0)
- Daily standups at 9 AM your time
- Milestone reviews every 24 hours

**Ready to launch? Say "GO" and we start NOW!** 🚀

---

**Document Version:** 2.0 (ONE WEEK SPRINT)
**Created:** 2026-02-09
**Status:** AWAITING APPROVAL ⏳
