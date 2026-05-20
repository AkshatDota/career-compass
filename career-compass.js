/* ===========================================================
   Career Compass — vanilla JS single-page app
   ===========================================================
   Integrated with FastAPI backend at API_BASE.
   - POST /api/session   → create session, get session_id
   - POST /api/answer    → save each answer (question_text + label(s))
   - GET  /api/results   → fetch AI-generated career recommendations

   Questions and navigation are handled client-side for instant UX.
   The backend receives human-readable question text + answer labels
   so the AI prompt has full context.
   =========================================================== */

(() => {
  'use strict';

  // ----------------------------------------------------------
  // Config
  // ----------------------------------------------------------
  // Empty string = relative URLs, so the app works on any host/port
  const API_BASE = '';

  // ----------------------------------------------------------
  // Utilities
  // ----------------------------------------------------------
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  const todayLabel = () => {
    const d = new Date();
    return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });
  };

  // ----------------------------------------------------------
  // Question bank (adaptive: ~12 questions)
  // Each option has tags that contribute weight to local scores,
  // and a human-readable label sent to the backend for the AI prompt.
  // ----------------------------------------------------------
  // Question bank — direction → job path OR business path
  // ----------------------------------------------------------
  const QUESTION_DIRECTION = {
    id: 'direction',
    text: 'What is your primary goal after BCA?',
    hint: 'This shapes everything that follows.',
    type: 'single',
    options: [
      { id: 'job',      label: 'Get a job — I want stable employment and a career',  tags: {} },
      { id: 'business', label: 'Start a business — I want to be my own boss',        tags: {} },
    ],
  };

  const QUESTIONS_JOB = [
    {
      id: 'sector',
      text: 'Which sector appeals to you more?',
      hint: 'This focuses your career matches.',
      type: 'single',
      options: [
        { id: 'private',    label: 'Private sector — faster growth, higher pay',               tags: { startup: 1, tech: 1 } },
        { id: 'government', label: 'Government / PSU — job security, pension, stability',       tags: { stability: 3, finance: 1 } },
        { id: 'open',       label: 'Open to both — show me the best option either way',         tags: {} },
      ],
    },
    {
      id: 'energy',
      text: 'What kind of work energizes you most?',
      hint: 'Pick the one that feels most true.',
      type: 'single',
      options: [
        { id: 'solve',   label: 'Solving complex, puzzle-like problems',     tags: { analytical: 3, tech: 2, data: 2 } },
        { id: 'help',    label: 'Helping people through tough moments',       tags: { people: 3, empathy: 3, care: 2 } },
        { id: 'create',  label: 'Creating things others can use or enjoy',    tags: { creative: 3, design: 2, craft: 2 } },
        { id: 'lead',    label: 'Bringing people together to ship something', tags: { leadership: 3, product: 2, people: 1 } },
        { id: 'analyze', label: 'Finding patterns in data and information',   tags: { data: 3, analytical: 3, research: 2 } },
      ],
    },
    {
      id: 'environment',
      text: 'Which work environment do you thrive in?',
      type: 'single',
      options: [
        { id: 'structured', label: 'Structured, predictable, well-defined',     tags: { stability: 3, finance: 2, ops: 2 } },
        { id: 'startup',    label: 'Fast-paced, ambiguous, lots of change',      tags: { startup: 3, risk: 2, product: 1 } },
        { id: 'quiet',      label: 'Quiet and independent — head-down work',     tags: { solo: 3, analytical: 1, craft: 1 } },
        { id: 'team',       label: 'Highly collaborative, lots of conversation', tags: { people: 3, leadership: 1, comms: 2 } },
      ],
    },
    {
      id: 'subjects',
      text: 'Which subjects did you actually enjoy in school or college?',
      hint: 'Pick all that apply.',
      type: 'multi',
      options: [
        { id: 'math',     label: 'Math & statistics',          tags: { analytical: 2, data: 2, finance: 1 } },
        { id: 'science',  label: 'Science & research',         tags: { research: 2, tech: 1, care: 1 } },
        { id: 'cs',       label: 'Computers & coding',         tags: { tech: 3, data: 1 } },
        { id: 'arts',     label: 'Arts & design',              tags: { creative: 3, design: 2 } },
        { id: 'lang',     label: 'Languages & literature',     tags: { creative: 1, comms: 2, craft: 1 } },
        { id: 'business', label: 'Business & economics',       tags: { finance: 2, product: 1, leadership: 1 } },
        { id: 'social',   label: 'Psychology & social studies',tags: { empathy: 3, people: 2, research: 1 } },
      ],
    },
    {
      id: 'communicate',
      text: 'How do you most naturally communicate ideas?',
      hint: 'Pick all that feel true for you.',
      type: 'multi',
      options: [
        { id: 'write',   label: 'In writing — clear, structured prose',   tags: { comms: 3, craft: 2, research: 1 } },
        { id: 'talk',    label: 'In conversation, face-to-face',          tags: { people: 3, leadership: 1, comms: 2 } },
        { id: 'visual',  label: 'Through visuals — sketches, diagrams',   tags: { creative: 3, design: 3 } },
        { id: 'numbers', label: 'With numbers, charts, and evidence',     tags: { data: 3, analytical: 2, finance: 1 } },
      ],
    },
    {
      id: 'values',
      text: 'What matters most in a job for you?',
      hint: 'Pick up to three.',
      type: 'multi',
      max: 3,
      options: [
        { id: 'pay',       label: 'High earning potential',    tags: { finance: 2, tech: 1, product: 1 } },
        { id: 'flex',      label: 'Flexibility — when & where',tags: { solo: 2, craft: 1, tech: 1 } },
        { id: 'impact',    label: 'Visible impact on people',  tags: { care: 3, empathy: 2, people: 1 } },
        { id: 'creative',  label: 'Creative expression',       tags: { creative: 3, design: 2, craft: 1 } },
        { id: 'stability', label: 'Stability and security',    tags: { stability: 3, finance: 1, ops: 1 } },
        { id: 'growth',    label: 'Fast skill growth',         tags: { startup: 2, tech: 1, product: 1 } },
      ],
    },
    {
      id: 'develop',
      text: 'Which skills would you genuinely enjoy developing?',
      hint: 'Pick all that interest you.',
      type: 'multi',
      options: [
        { id: 'code',      label: 'Coding & engineering',         tags: { tech: 3 } },
        { id: 'design',    label: 'Visual & product design',      tags: { design: 3, creative: 2 } },
        { id: 'speak',     label: 'Public speaking & presenting', tags: { leadership: 2, comms: 2, people: 1 } },
        { id: 'write',     label: 'Writing & storytelling',       tags: { comms: 3, craft: 2 } },
        { id: 'research',  label: 'Research & investigation',     tags: { research: 3, analytical: 1 } },
        { id: 'negotiate', label: 'Negotiation & persuasion',     tags: { leadership: 2, people: 1, finance: 1 } },
        { id: 'data',      label: 'Data analysis & modelling',    tags: { data: 3, analytical: 2 } },
        { id: 'counsel',   label: 'Listening & counselling',      tags: { empathy: 3, care: 2 } },
      ],
    },
    {
      id: 'problem',
      text: 'When you hit a tricky problem, what do you usually do?',
      type: 'single',
      options: [
        { id: 'break',    label: 'Break it down into smaller steps',    tags: { analytical: 3, ops: 1 } },
        { id: 'brain',    label: 'Brainstorm wildly, then pick one',    tags: { creative: 3, startup: 1 } },
        { id: 'research', label: 'Research thoroughly before acting',   tags: { research: 3, analytical: 1 } },
        { id: 'ask',      label: 'Ask others — bounce it off the team', tags: { people: 3, leadership: 1, comms: 1 } },
      ],
    },
    {
      id: 'workday',
      text: 'Describe your ideal workday.',
      type: 'single',
      options: [
        { id: 'focus', label: 'Long stretches of deep focus, alone',          tags: { solo: 3, craft: 2, analytical: 1 } },
        { id: 'meet',  label: 'Lots of conversations & meetings',             tags: { leadership: 2, people: 3 } },
        { id: 'build', label: 'Hands-on building — making something tangible',tags: { craft: 2, tech: 2, design: 2 } },
        { id: 'mix',   label: 'A bit of everything — variety daily',          tags: { product: 3, startup: 1, leadership: 1 } },
      ],
    },
    {
      id: 'risk',
      text: 'How do you feel about uncertainty and risk?',
      type: 'single',
      options: [
        { id: 'love',   label: 'Love it — uncertainty is energising',  tags: { startup: 3, risk: 3 } },
        { id: 'ok',     label: 'Comfortable, in measured doses',        tags: { product: 1, startup: 1, leadership: 1 } },
        { id: 'prefer', label: 'Prefer some predictability',            tags: { stability: 2, ops: 1 } },
        { id: 'avoid',  label: 'Strongly prefer stable, clear paths',   tags: { stability: 3, finance: 2, care: 1 } },
      ],
    },
    {
      id: 'drawn',
      text: 'You feel most drawn to working with…',
      hint: 'Pick up to two.',
      type: 'multi',
      max: 2,
      options: [
        { id: 'people', label: 'People — relationships, behaviour',   tags: { people: 3, empathy: 2, care: 2 } },
        { id: 'ideas',  label: 'Ideas — concepts, theory, stories',   tags: { creative: 2, research: 2, craft: 1 } },
        { id: 'things', label: 'Things — making, crafting, building', tags: { craft: 3, design: 1, tech: 1 } },
        { id: 'data',   label: 'Data — numbers, systems, signals',    tags: { data: 3, analytical: 2 } },
      ],
    },
    {
      id: 'fiveyears',
      text: 'Where do you hope to be in five years?',
      type: 'single',
      options: [
        { id: 'lead',    label: 'Leading a team in a respected company',        tags: { leadership: 3, product: 1, finance: 1 } },
        { id: 'own',     label: 'Running my own thing',                         tags: { startup: 3, leadership: 1 } },
        { id: 'expert',  label: 'A recognised expert in my craft',              tags: { craft: 3, tech: 1, design: 1 } },
        { id: 'mission', label: 'Making real impact for a cause I care about',  tags: { care: 3, empathy: 2, people: 1 } },
      ],
    },
    {
      id: 'study',
      text: 'How much weight should we give to formal study time?',
      hint: 'Some careers need more upfront training than others.',
      type: 'single',
      options: [
        { id: 'short',  label: 'Less — I want to start working soon',    tags: { startup: 1, design: 1, comms: 1 } },
        { id: 'medium', label: 'A few years is fine',                     tags: { tech: 1, product: 1, finance: 1, data: 1 } },
        { id: 'long',   label: "I'm happy to invest in long study",       tags: { care: 2, research: 2, analytical: 1 } },
      ],
    },
    {
      id: 'location',
      text: 'Which type of city are you currently based in?',
      hint: 'Helps us match careers with your local job market.',
      type: 'single',
      options: [
        { id: 'metro',  label: 'Metro city (Delhi / Mumbai / Bangalore / Hyderabad / Chennai)', tags: { startup: 1, tech: 1, finance: 1 } },
        { id: 'tier2',  label: 'Mid-size city (Pune / Ahmedabad / Jaipur / Kochi etc.)',        tags: { stability: 1 } },
        { id: 'tier3',  label: 'Small town or rural area',                                       tags: { stability: 2 } },
        { id: 'abroad', label: 'Planning to relocate or go abroad',                              tags: { startup: 1, risk: 1 } },
      ],
    },
    {
      id: 'academics',
      text: 'How would you honestly rate your academic performance so far?',
      type: 'single',
      options: [
        { id: 'top',   label: 'Top of my class',                            tags: { research: 2, analytical: 1 } },
        { id: 'above', label: 'Above average',                              tags: { analytical: 1 } },
        { id: 'avg',   label: 'Average',                                    tags: {} },
        { id: 'doer',  label: "Below average — I learn better by doing",    tags: { craft: 1, startup: 1 } },
      ],
    },
    {
      id: 'constraint',
      text: 'What is your biggest concern right now?',
      hint: 'Being honest helps us give you realistic, grounded guidance.',
      type: 'single',
      options: [
        { id: 'money',  label: 'Financial pressure — I need to earn soon',       tags: { stability: 2, finance: 1 } },
        { id: 'family', label: 'Family expectations about my career choice',      tags: { stability: 1 } },
        { id: 'unsure', label: 'Unsure of my own strengths and direction',        tags: {} },
        { id: 'free',   label: 'No specific concerns — I am fairly free to choose', tags: { startup: 1, risk: 1 } },
      ],
    },
  ];

  const QUESTIONS_BUSINESS = [
    {
      id: 'biz_type',
      text: 'What kind of business excites you most?',
      hint: 'Pick the one that genuinely gets you going.',
      type: 'single',
      options: [
        { id: 'tech',      label: 'Tech / Software — app, SaaS, or digital product',           tags: { tech: 3, startup: 2 } },
        { id: 'service',   label: 'Service business — agency, freelancing, or consulting',      tags: { people: 2, craft: 2 } },
        { id: 'retail',    label: 'Retail / E-commerce — sell physical or online products',     tags: { ops: 2, finance: 1 } },
        { id: 'food',      label: 'Food & Beverage — restaurant, cloud kitchen, or catering',   tags: { ops: 2, people: 1 } },
        { id: 'education', label: 'Education / Coaching — teach, tutor, or upskill others',    tags: { people: 3, comms: 2 } },
        { id: 'creative',  label: 'Creative / Content — design, media, or entertainment',       tags: { creative: 3, comms: 2 } },
      ],
    },
    {
      id: 'biz_investment',
      text: 'How much can you realistically invest to get started?',
      hint: 'Be honest — this shapes what is actually possible for you.',
      type: 'single',
      options: [
        { id: 'bootstrap', label: 'Almost nothing — under ₹10,000 (pure bootstrap)',           tags: { stability: 1 } },
        { id: 'small',     label: '₹10,000 – ₹1 Lakh — small savings or family support',      tags: {} },
        { id: 'medium',    label: '₹1 Lakh – ₹10 Lakh — small loan or pooled savings',        tags: { risk: 1 } },
        { id: 'large',     label: '₹10 Lakh+ — solid backing or investors in mind',            tags: { risk: 2, startup: 1 } },
      ],
    },
    {
      id: 'biz_location',
      text: 'Where do you plan to operate or expand?',
      hint: 'Your city and reach shapes which ideas are realistic right now.',
      type: 'single',
      options: [
        { id: 'metro',      label: 'Metro city (Delhi / Mumbai / Bangalore / Hyderabad / Chennai)', tags: { startup: 1 } },
        { id: 'tier2',      label: 'Mid-size city (Pune / Jaipur / Indore / Lucknow etc.)',         tags: {} },
        { id: 'small_town', label: 'Small town or rural area',                                       tags: { stability: 1 } },
        { id: 'online',     label: 'Fully online — location does not matter',                        tags: { tech: 1, startup: 1 } },
      ],
    },
    {
      id: 'biz_idea',
      text: 'Do you already have a specific business idea?',
      type: 'single',
      options: [
        { id: 'clear', label: 'Yes — a clear idea, I just need direction and a plan', tags: {} },
        { id: 'rough', label: 'Somewhat — a rough concept but nothing solid yet',     tags: {} },
        { id: 'none',  label: 'Not yet — I need help figuring out the right path',   tags: {} },
      ],
    },
    {
      id: 'biz_customer',
      text: 'Who would your primary customers be?',
      type: 'single',
      options: [
        { id: 'local',    label: 'Regular people in my city or nearby (B2C, local)',  tags: { people: 2 } },
        { id: 'online',   label: 'Anyone across India via the internet (B2C, online)',tags: { tech: 1, startup: 1 } },
        { id: 'business', label: 'Other businesses or professionals (B2B)',            tags: { finance: 1, leadership: 1 } },
        { id: 'unsure',   label: 'Not sure yet',                                      tags: {} },
      ],
    },
    {
      id: 'biz_strength',
      text: 'What is your biggest personal strength?',
      hint: 'The best businesses are built on real strengths, not wishful thinking.',
      type: 'single',
      options: [
        { id: 'tech_skill', label: 'Technical skills — coding, design, or building things',    tags: { tech: 2, craft: 2 } },
        { id: 'sales',      label: 'Sales & persuasion — I can convince and close people',     tags: { people: 2, leadership: 1 } },
        { id: 'network',    label: 'Connections — I know a lot of the right people',           tags: { people: 1, leadership: 1 } },
        { id: 'creative',   label: 'Creativity — I constantly come up with fresh ideas',       tags: { creative: 3 } },
        { id: 'ops',        label: 'Discipline & operations — I am organised and consistent',  tags: { ops: 2, stability: 1 } },
      ],
    },
    {
      id: 'biz_timeline',
      text: 'When are you aiming to launch?',
      type: 'single',
      options: [
        { id: 'asap',  label: 'As soon as possible — within 3 months',          tags: { risk: 1 } },
        { id: 'soon',  label: 'Within 6 months — once I feel prepared',         tags: {} },
        { id: 'year',  label: 'In about a year — I want to plan it properly',   tags: { stability: 1 } },
        { id: 'later', label: 'No rush yet — I am still exploring options',     tags: { stability: 1 } },
      ],
    },
  ];

  // ----------------------------------------------------------
  // Real API layer
  // ----------------------------------------------------------
  async function api(path, options = {}, timeoutMs = 30000) {
    const ctrl = new AbortController();
    const tid  = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
      const res = await fetch(API_BASE + path, {
        headers: { 'Content-Type': 'application/json' },
        signal: ctrl.signal,
        ...options,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      return res.json();
    } catch (e) {
      if (e.name === 'AbortError') throw new Error('Request timed out. Please check your connection and try again.');
      throw e;
    } finally {
      clearTimeout(tid);
    }
  }

  async function createSession() {
    const data = await api('/api/session', { method: 'POST' });
    localStorage.setItem('cc_session_id', data.session_id);
    localStorage.removeItem('cc_has_results');
    return data.session_id;
  }

  async function postAnswer(sessionId, question, selectedIds) {
    // Translate option IDs → human-readable labels for the AI prompt
    const labels = selectedIds.map(id => {
      const opt = question.options.find(o => o.id === id);
      return opt ? opt.label : id;
    });
    const answerPayload = labels.length === 1 ? labels[0] : labels;

    await api('/api/answer', {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        question_id: question.id,
        question_text: question.text,
        answer: answerPayload,
      }),
    });
  }

  async function fetchResults(sessionId) {
    return api(`/api/results?session_id=${encodeURIComponent(sessionId)}`, {}, 90000);
  }

  // ----------------------------------------------------------
  // Normalise AI result → consistent shape for renderResults()
  // ----------------------------------------------------------
  function _parseRoadmap(raw) {
    if (!raw) return [];
    return raw.map(step => {
      if (typeof step !== 'string') return { title: step.title || step, desc: step.desc || '' };
      const body = step.replace(/^Step\s*\d+[:.]\s*/i, '');
      const sep  = body.search(/\s[—–-]\s/);
      return sep > -1
        ? { title: body.slice(0, sep).trim(), desc: body.slice(sep + 3).trim() }
        : { title: body, desc: '' };
    });
  }

  function normalizeResults(data) {
    const summary = Array.isArray(data.summary)
      ? data.summary : (data.summary ? [data.summary] : []);

    // Business path
    if (data.businesses) {
      const businesses = (data.businesses || []).map(b => ({
        title:    b.title || 'Business Idea',
        match:    b.match_score || null,
        tagline:  b.tagline || '',
        fit:      b.why_it_fits || '',
        investment: [
          { stage: 'Minimum',    label: 'To get started',   range: b.investment?.minimum    || '—' },
          { stage: 'Comfortable',label: 'Proper launch',    range: b.investment?.comfortable || '—' },
          { stage: 'To scale',   label: 'Growth phase',     range: b.investment?.to_scale    || '—' },
        ],
        revenue: [
          { stage: 'Year 1',  label: 'First year',   range: b.revenue_potential?.year1    || '—' },
          { stage: 'Year 3',  label: 'Established',  range: b.revenue_potential?.year3    || '—' },
          { stage: 'At scale',label: 'Growth phase', range: b.revenue_potential?.at_scale || '—' },
        ],
        skills:    b.skills_to_build || [],
        roadmap:   _parseRoadmap(b.roadmap),
        resources: b.resources || [],
      }));
      return { type: 'business', generatedOn: todayLabel(), businesses, summary };
    }

    // Job path
    const careers = (data.careers || []).map(c => {
      const salary = Array.isArray(c.salary) ? c.salary : [
        { stage: 'Fresher',   years: '0–1 yr',  range: c.salary?.fresher   || '—' },
        { stage: 'Mid-level', years: '3–5 yrs', range: c.salary?.mid_level || '—' },
        { stage: 'Senior',    years: '10+ yrs', range: c.salary?.senior    || '—' },
      ];
      return {
        title:     c.title,
        tagline:   c.tagline,
        fit:       c.why_it_fits || c.fit || '',
        salary,
        skills:    c.skills_to_build || c.skills || [],
        roadmap:   _parseRoadmap(c.roadmap),
        companies: c.top_companies || [],
        match:     c.match_score   || c.match || null,
      };
    });
    return { type: 'job', generatedOn: todayLabel(), careers, summary };
  }

  // ----------------------------------------------------------
  // State
  // ----------------------------------------------------------
  const state = {
    sessionId:        null,
    name:             'Nandini',
    gender:           'female',
    path:             null,   // 'job' | 'business' — set after direction Q
    history:          [],
    answers:          {},
    currentQuestion:  null,
    currentSelection: [],
    results:          null,
  };

  function activeQuestions() {
    return state.path === 'business' ? QUESTIONS_BUSINESS : QUESTIONS_JOB;
  }

  function totalQuestions() {
    return 1 + activeQuestions().length; // 1 for the direction Q
  }

  // ----------------------------------------------------------
  // Screen routing
  // ----------------------------------------------------------
  function showScreen(name) {
    $$('.screen').forEach(s => s.classList.remove('active'));
    const el = document.getElementById('screen-' + name);
    if (el) el.classList.add('active');
    window.scrollTo({ top: 0, behavior: 'instant' });
  }

  // ----------------------------------------------------------
  // Question rendering
  // ----------------------------------------------------------
  function renderQuestion(q) {
    state.currentQuestion = q;
    state.currentSelection = state.answers[q.id]
      ? (Array.isArray(state.answers[q.id]) ? [...state.answers[q.id]] : [state.answers[q.id]])
      : [];

    const body = $('#questionBody');

    const optionsHtml = q.options.map(opt => {
      const selected = state.currentSelection.includes(opt.id);
      return `
        <button class="option ${q.type === 'single' ? 'single' : ''} ${selected ? 'selected' : ''}"
                data-opt="${opt.id}">
          <span class="check">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"
                 stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          </span>
          <span>${opt.label}</span>
        </button>
      `;
    }).join('');

    body.innerHTML = `
      <div class="question fade-swap">
        <div class="question-kicker">${q.type === 'multi' ? 'Choose any that apply' : 'Choose one'}</div>
        <h2 class="question-text">${q.text}</h2>
        ${q.hint
          ? `<p class="question-hint">${q.hint}</p>`
          : '<div class="question-hint" style="visibility:hidden;">.</div>'}
        <div class="options" id="optionsList">${optionsHtml}</div>
        <div class="continue-row" id="continueRow"></div>
      </div>
    `;

    $$('.option', body).forEach(btn => {
      btn.addEventListener('click', () => onOptionClick(btn.dataset.opt, btn));
    });

    updateContinueButton();

    const idx = state.history.length;
    const total = state.path ? totalQuestions() : '?';
    $('#qNum').textContent = idx + 1;
    $('#qTotal').textContent = total;
    const pct = state.path ? Math.min(100, ((idx + 0.5) / totalQuestions()) * 100) : 5;
    $('#progressFill').style.width = pct + '%';
    $('#backBtn').disabled = state.history.length <= 1;
  }

  function onOptionClick(optId, btnEl) {
    const q = state.currentQuestion;
    if (q.type === 'single') {
      state.currentSelection = [optId];
      $$('.option').forEach(b => b.classList.remove('selected'));
      btnEl.classList.add('selected', 'flash');
      setTimeout(() => submitAnswer(), 320);
    } else {
      const i = state.currentSelection.indexOf(optId);
      if (i >= 0) {
        state.currentSelection.splice(i, 1);
        btnEl.classList.remove('selected');
      } else {
        if (q.max && state.currentSelection.length >= q.max) {
          const oldest = state.currentSelection.shift();
          const oldBtn = document.querySelector(`.option[data-opt="${oldest}"]`);
          if (oldBtn) oldBtn.classList.remove('selected');
        }
        state.currentSelection.push(optId);
        btnEl.classList.add('selected', 'flash');
      }
      updateContinueButton();
    }
  }

  function updateContinueButton() {
    const q = state.currentQuestion;
    const row = $('#continueRow');
    if (!row || q.type !== 'multi') { if (row) row.innerHTML = ''; return; }
    if (state.currentSelection.length === 0) {
      row.innerHTML = '';
    } else {
      row.innerHTML = `<button class="btn btn-accent" id="continueBtn">Continue &nbsp;→</button>`;
      $('#continueBtn').addEventListener('click', () => submitAnswer());
    }
  }

  function showInlineError(msg) {
    let el = document.getElementById('inline-error');
    if (!el) {
      el = document.createElement('div');
      el.id = 'inline-error';
      el.style.cssText = [
        'background:#fee2e2', 'color:#991b1b', 'border-radius:8px',
        'padding:10px 16px', 'margin:12px 0 0', 'font-size:14px',
        'text-align:center',
      ].join(';');
      const qBody = document.getElementById('questionBody');
      if (qBody) qBody.insertAdjacentElement('beforebegin', el);
    }
    el.textContent = msg;
    setTimeout(() => el?.remove(), 6000);
  }

  async function submitAnswer() {
    const q = state.currentQuestion;
    const answer = q.type === 'single'
      ? state.currentSelection[0]
      : [...state.currentSelection];

    state.answers[q.id] = answer;
    if (!state.history.find(h => h.id === q.id)) state.history.push(q);

    // Save to backend — must succeed before advancing
    try {
      await postAnswer(state.sessionId, q, Array.isArray(answer) ? answer : [answer]);
    } catch (err) {
      console.warn('Answer save failed:', err);
      showInlineError('Could not save your answer — check your connection and try again.');
      return;
    }

    // Direction Q → set path and start the right question list
    if (q.id === 'direction') {
      state.path = answer; // 'job' | 'business'
      localStorage.setItem('cc_path', answer);
      renderQuestion(activeQuestions()[0]);
      return;
    }

    // Advance within the active question list
    const list = activeQuestions();
    const nextIdx = list.findIndex(x => x.id === q.id) + 1;
    if (nextIdx >= list.length) {
      await fetchAndShowResults();
    } else {
      renderQuestion(list[nextIdx]);
    }
  }

  function goBack() {
    if (state.history.length <= 1) return;
    state.history.pop();
    const prev = state.history[state.history.length - 1];
    state.history.pop();
    renderQuestion(prev);
  }

  // ----------------------------------------------------------
  // Loading screen
  // ----------------------------------------------------------
  const LOADING_MESSAGES = {
    job: [
      "Analysing Nandini's answers…",
      'Mapping career paths…',
      'Calculating salary ranges…',
      "Building Nandini's roadmap…",
    ],
    business: [
      "Analysing Nandini's answers…",
      'Exploring business opportunities…',
      'Calculating investment & revenue…',
      "Building Nandini's business roadmap…",
    ],
  };
  let loadingTimer = null;
  let loadingSlowTimer = null;

  function startLoading() {
    showScreen('loading');
    const msgs = LOADING_MESSAGES[state.path] || LOADING_MESSAGES.job;
    const titleEl = $('#loadingTitle');
    const subEl = $('#loadingSub');
    let i = 0;
    titleEl.textContent = msgs[0];
    clearInterval(loadingTimer);
    clearTimeout(loadingSlowTimer);
    loadingTimer = setInterval(() => {
      i = (i + 1) % msgs.length;
      titleEl.style.opacity = 0;
      setTimeout(() => {
        titleEl.textContent = msgs[i];
        titleEl.style.opacity = 1;
      }, 200);
    }, 2000);
    // After 15s, show a reassuring message so the user doesn't think it's broken
    loadingSlowTimer = setTimeout(() => {
      if (subEl) subEl.textContent = 'Still thinking… the AI is being thorough. Almost there!';
    }, 15000);
  }

  function stopLoading() {
    clearInterval(loadingTimer);
    clearTimeout(loadingSlowTimer);
    loadingTimer = null;
  }

  async function fetchAndShowResults() {
    startLoading();
    const minTime = new Promise(r => setTimeout(r, 2400));
    try {
      const [raw] = await Promise.all([
        fetchResults(state.sessionId),
        minTime,
      ]);
      state.results = normalizeResults(raw);
      localStorage.setItem('cc_has_results', state.sessionId);
      stopLoading();
      renderResults(state.results);
      showScreen('results');
    } catch (e) {
      stopLoading();
      console.error('Results error:', e);
      showError(e.message);
    }
  }

  // ----------------------------------------------------------
  // Results rendering
  // ----------------------------------------------------------
  function _roadmapHtml(roadmap) {
    return `<ol class="roadmap">${roadmap.map(step => `
      <li><div>
        <span class="step-title">${step.title}</span>
        ${step.desc ? `<span class="step-desc">${step.desc}</span>` : ''}
      </div></li>`).join('')}</ol>`;
  }

  function renderResults(data) {
    $('#headerMeta').textContent = data.generatedOn;
    $('#resultsFootnote').textContent = "Career Compass · Nandini's Report";
    if (data.type === 'business') {
      _renderBusinessResults(data);
    } else {
      _renderCareerResults(data);
    }
  }

  function _renderCareerResults(data) {
    const wrap = $('#resultsWrap');
    const cards = data.careers.map((c, i) => `
      <article class="career-card">
        <div class="career-rank">Match ${String(i + 1).padStart(2, '0')}</div>
        ${c.match ? `<div class="career-match">${c.match}% match</div>` : ''}
        <h3 class="career-title">${c.title}</h3>
        <p class="career-tagline">${c.tagline}</p>
        <div class="career-section">
          <p class="career-section-h">Why this fits you</p>
          <p class="career-fit">${c.fit}</p>
        </div>
        <div class="career-section">
          <p class="career-section-h">Salary expectations · India</p>
          <table class="salary-table">
            ${c.salary.map(s => `<tr>
              <td><span class="role-stage">${s.stage}</span><span class="years">${s.years}</span></td>
              <td>${s.range}</td>
            </tr>`).join('')}
          </table>
        </div>
        <div class="career-section">
          <p class="career-section-h">Skills to build</p>
          <div class="skills">${c.skills.map(s => `<span class="skill-tag">${s}</span>`).join('')}</div>
        </div>
        <div class="career-section">
          <p class="career-section-h">Your roadmap</p>
          ${_roadmapHtml(c.roadmap)}
        </div>
        ${c.companies.length ? `
        <div class="career-section">
          <p class="career-section-h">Top companies hiring</p>
          <div class="skills">${c.companies.map(co => `<span class="skill-tag">${co}</span>`).join('')}</div>
        </div>` : ''}
      </article>`).join('');

    wrap.innerHTML = `
      <header class="results-header">
        <div class="results-eyebrow">Nandini's Career Report</div>
        <h1 class="results-title">Nandini, here are your paths.</h1>
        <p class="results-sub">Based on your answers — real Indian salary data, active hiring companies, and a step-by-step roadmap.</p>
        <div class="results-meta">
          <div><strong>${data.generatedOn}</strong>Report date</div>
          <div><strong>${data.careers.length} careers</strong>Top matches</div>
          <div><strong>${Object.keys(state.answers).length} answers</strong>Inputs analysed</div>
        </div>
      </header>
      ${cards}
      <section class="next-section">
        <h3>What to do next</h3>
        <ul>${data.summary.map(s => `<li>${s}</li>`).join('')}</ul>
      </section>`;
  }

  function _renderBusinessResults(data) {
    const wrap = $('#resultsWrap');
    const cards = data.businesses.map((b, i) => `
      <article class="career-card">
        <div class="career-rank">Idea ${String(i + 1).padStart(2, '0')}</div>
        ${b.match ? `<div class="career-match">${b.match}% match</div>` : ''}
        <h3 class="career-title">${b.title}</h3>
        <p class="career-tagline">${b.tagline}</p>
        <div class="career-section">
          <p class="career-section-h">Why this fits you</p>
          <p class="career-fit">${b.fit}</p>
        </div>
        <div class="career-section">
          <p class="career-section-h">Investment required · India</p>
          <table class="salary-table">
            ${b.investment.map(row => `<tr>
              <td><span class="role-stage">${row.stage}</span><span class="years">${row.label}</span></td>
              <td>${row.range}</td>
            </tr>`).join('')}
          </table>
        </div>
        <div class="career-section">
          <p class="career-section-h">Revenue potential · India</p>
          <table class="salary-table">
            ${b.revenue.map(row => `<tr>
              <td><span class="role-stage">${row.stage}</span><span class="years">${row.label}</span></td>
              <td>${row.range}</td>
            </tr>`).join('')}
          </table>
        </div>
        <div class="career-section">
          <p class="career-section-h">Skills to build</p>
          <div class="skills">${b.skills.map(s => `<span class="skill-tag">${s}</span>`).join('')}</div>
        </div>
        <div class="career-section">
          <p class="career-section-h">Your launch roadmap</p>
          ${_roadmapHtml(b.roadmap)}
        </div>
        ${b.resources.length ? `
        <div class="career-section">
          <p class="career-section-h">Where to start in India</p>
          <div class="skills">${b.resources.map(r => `<span class="skill-tag">${r}</span>`).join('')}</div>
        </div>` : ''}
      </article>`).join('');

    wrap.innerHTML = `
      <header class="results-header">
        <div class="results-eyebrow">Nandini's Business Report</div>
        <h1 class="results-title">Nandini, here are your ventures.</h1>
        <p class="results-sub">Based on your answers — real Indian investment figures, revenue potential, and a step-by-step launch roadmap.</p>
        <div class="results-meta">
          <div><strong>${data.generatedOn}</strong>Report date</div>
          <div><strong>${data.businesses.length} ideas</strong>Top matches</div>
          <div><strong>${Object.keys(state.answers).length} answers</strong>Inputs analysed</div>
        </div>
      </header>
      ${cards}
      <section class="next-section">
        <h3>What to do next</h3>
        <ul>${data.summary.map(s => `<li>${s}</li>`).join('')}</ul>
      </section>`;
  }

  // ----------------------------------------------------------
  // Error handling
  // ----------------------------------------------------------
  function showError(msg) {
    stopLoading();
    const desc = $('#screen-error .welcome-desc');
    if (desc && msg) desc.textContent = msg;
    showScreen('error');
  }

  // ----------------------------------------------------------
  // Restart / new session
  // ----------------------------------------------------------
  async function restart() {
    state.history          = [];
    state.answers          = {};
    state.path             = null;
    state.currentQuestion  = null;
    state.currentSelection = [];
    state.results          = null;
    localStorage.removeItem('cc_path');
    $('#headerMeta').textContent = '';
    document.getElementById('resumeBtn')?.remove();

    try {
      state.sessionId = await createSession(); // createSession clears cc_has_results
    } catch (e) {
      console.warn('Could not create session:', e);
    }

    showScreen('welcome');
  }

  // ----------------------------------------------------------
  // PDF download
  // ----------------------------------------------------------
  function downloadPDF() {
    const wrap = document.getElementById('resultsWrap');
    if (!window.html2pdf || !wrap) { window.print(); return; }

    // Clone into a detached node at body level so no ancestor CSS (.screen, overflow:hidden, etc.)
    // can interfere with html2canvas capture.
    const clone = wrap.cloneNode(true);
    clone.style.cssText = [
      'position:absolute', 'left:-9999px', 'top:0',
      'width:794px', 'background:#ffffff', 'padding:24px',
    ].join(';');
    document.body.appendChild(clone);

    html2pdf().set({
      margin:      [12, 12, 12, 12],
      filename:    "Nandini's Career Report.pdf",
      image:       { type: 'jpeg', quality: 0.97 },
      html2canvas: { scale: 2, useCORS: true, allowTaint: true, backgroundColor: '#ffffff', windowWidth: 794 },
      jsPDF:       { unit: 'mm', format: 'a4', orientation: 'portrait' },
      pagebreak:   { mode: ['avoid-all', 'css', 'legacy'] },
    }).from(clone).save().finally(() => document.body.removeChild(clone));
  }

  // ----------------------------------------------------------
  // Boot
  // ----------------------------------------------------------
  async function boot() {
    const storedSid  = localStorage.getItem('cc_session_id');
    const hasResults = localStorage.getItem('cc_has_results');
    state.path = localStorage.getItem('cc_path') || null;

    if (storedSid) {
      state.sessionId = storedSid;
      if (hasResults === storedSid) {
        // Previous quiz completed — offer to view results without re-doing the quiz
        const resumeBtn = document.createElement('button');
        resumeBtn.id = 'resumeBtn';
        resumeBtn.className = 'btn btn-ghost';
        resumeBtn.style.cssText = 'margin-top:12px;font-size:14px;display:block;width:100%;';
        resumeBtn.textContent = 'View previous results →';
        resumeBtn.addEventListener('click', fetchAndShowResults);
        const beginBtn = document.getElementById('beginBtn');
        if (beginBtn) beginBtn.insertAdjacentElement('afterend', resumeBtn);
      }
    } else {
      try {
        state.sessionId = await createSession();
      } catch (e) {
        console.warn('Backend unavailable, using local session:', e.message);
        state.sessionId = crypto.randomUUID?.() || Date.now().toString(36);
        localStorage.setItem('cc_session_id', state.sessionId);
      }
    }

    $('#beginBtn').addEventListener('click', async () => {
      // Always start a fresh quiz — clear old session state
      document.getElementById('resumeBtn')?.remove();
      state.history = [];
      state.answers = {};
      try {
        state.sessionId = await createSession();
      } catch (e) {
        console.warn('Could not create session:', e.message);
      }

      // Post name and gender as the first two answers so the AI prompt knows them
      try {
        await postAnswer(state.sessionId,
          { id: 'user_name',   text: 'What is your name?',   options: [] }, [state.name]);
        await postAnswer(state.sessionId,
          { id: 'user_gender', text: 'What are your pronouns?', options: [] }, [state.gender]);
      } catch (e) {
        console.warn('Could not save name/gender:', e.message);
      }

      state.path = null;
      localStorage.removeItem('cc_path');
      renderQuestion(QUESTION_DIRECTION);
      showScreen('question');
    });

    $('#backBtn').addEventListener('click', goBack);
    $('#downloadBtn').addEventListener('click', downloadPDF);
    $('#restartBtn').addEventListener('click', restart);

    $('#retryBtn').addEventListener('click', () => {
      if (Object.keys(state.answers).length > 0) {
        fetchAndShowResults();
      } else {
        restart();
      }
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && document.getElementById('screen-welcome').classList.contains('active')) {
        $('#beginBtn').click();
      }
    });

    showScreen('welcome');
  }

  document.addEventListener('DOMContentLoaded', boot);
})();
