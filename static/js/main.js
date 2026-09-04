document.documentElement.classList.replace('no-js', 'js');

const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const navToggle = document.querySelector('.nav-toggle');
const siteNav = document.querySelector('.site-nav');

if (navToggle && siteNav) {
  navToggle.addEventListener('click', () => {
    const isOpen = navToggle.getAttribute('aria-expanded') === 'true';
    navToggle.setAttribute('aria-expanded', String(!isOpen));
    siteNav.classList.toggle('is-open', !isOpen);
  });

  siteNav.addEventListener('click', (event) => {
    if (event.target.closest('a')) {
      navToggle.setAttribute('aria-expanded', 'false');
      siteNav.classList.remove('is-open');
    }
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      navToggle.setAttribute('aria-expanded', 'false');
      siteNav.classList.remove('is-open');
      navToggle.focus();
    }
  });
}

const year = document.querySelector('#current-year');
if (year) year.textContent = new Date().getFullYear();

const heroVisual = document.querySelector('.hero-visual');
const heroStatus = document.querySelector('.system-status');
const heroStates = ['detecting', 'reviewing', 'validating', 'approved'];
let heroTimer;

function runHeroSystem() {
  if (!heroVisual || !heroStatus || heroTimer) return;
  const label = heroStatus.querySelector('strong span');
  let index = 0;
  heroVisual.classList.add('is-active');
  label.textContent = heroStates[index];

  if (reducedMotion.matches) {
    label.textContent = 'approved';
    heroStatus.classList.add('is-approved');
    heroVisual.classList.remove('is-active');
    return;
  }

  heroTimer = window.setInterval(() => {
    index += 1;
    label.textContent = heroStates[index];
    if (index === heroStates.length - 1) {
      window.clearInterval(heroTimer);
      heroTimer = null;
      heroStatus.classList.add('is-approved');
      heroVisual.classList.remove('is-active');
    }
  }, 850);
}

if (heroVisual) {
  heroVisual.addEventListener('pointerenter', runHeroSystem, { once: true });
  heroVisual.addEventListener('focus', runHeroSystem, { once: true });
}

document.querySelectorAll('.demo-status').forEach((demo) => {
  const trigger = demo.querySelector('.demo-trigger');
  const output = demo.querySelector('.demo-step');
  const sequence = demo.dataset.sequence.split('|');
  let running = false;

  const runDemo = () => {
    if (running) return;
    running = true;
    trigger.disabled = true;
    let index = 0;

    const showStep = () => {
      output.classList.add('is-changing');
      window.setTimeout(() => {
        output.textContent = sequence[index];
        output.classList.remove('is-changing');
        index += 1;

        if (index < sequence.length && !reducedMotion.matches) {
          window.setTimeout(showStep, 720);
        } else {
          if (reducedMotion.matches) output.textContent = sequence[sequence.length - 1];
          running = false;
          trigger.disabled = false;
          trigger.textContent = 'Run again';
        }
      }, reducedMotion.matches ? 0 : 130);
    };

    showStep();
  };

  trigger.addEventListener('click', runDemo);
  demo.closest('.project-card').addEventListener('pointerenter', runDemo, { once: true });
});

document.querySelectorAll('.note-toggle').forEach((toggle) => {
  toggle.addEventListener('click', () => {
    const expanded = toggle.getAttribute('aria-expanded') === 'true';
    const detail = document.getElementById(toggle.getAttribute('aria-controls'));
    toggle.setAttribute('aria-expanded', String(!expanded));
    toggle.querySelector('.note-control span').textContent = expanded ? 'Read note' : 'Close note';
    toggle.closest('.note-card').classList.toggle('is-expanded', !expanded);
    detail.setAttribute('aria-hidden', String(expanded));
  });
});

const revealTargets = document.querySelectorAll('.section-heading, .project-card, .now-grid, .note-card, .about-grid');
revealTargets.forEach((target) => target.classList.add('reveal'));

if ('IntersectionObserver' in window && !reducedMotion.matches) {
  const revealObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -32px' });
  revealTargets.forEach((target) => revealObserver.observe(target));
} else {
  revealTargets.forEach((target) => target.classList.add('is-visible'));
}

const curator = document.querySelector('[data-curator]');
if (curator) {
  const inspectButton = curator.querySelector('.curator-trigger');
  const progress = curator.querySelector('.inspection-progress');
  const progressText = progress.querySelector('strong');
  const results = curator.querySelector('.inspection-results');
  const finding = curator.querySelector('.finding-select');
  const repair = curator.querySelector('[data-repair]');
  const previewButton = curator.querySelector('.repair-preview-trigger');
  const approveButton = curator.querySelector('.approve-trigger');
  const validation = curator.querySelector('.repair-validation');
  const inspectionSteps = ['Inspecting content…', 'Checking relationships…', 'Checking provenance…', '2 findings detected'];

  const runSequence = (steps, onStep, onComplete) => {
    if (reducedMotion.matches) {
      onStep(steps[steps.length - 1]);
      onComplete();
      return;
    }
    let step = 0;
    onStep(steps[step]);
    const timer = window.setInterval(() => {
      step += 1;
      onStep(steps[step]);
      if (step === steps.length - 1) {
        window.clearInterval(timer);
        onComplete();
      }
    }, 650);
  };

  inspectButton.addEventListener('click', () => {
    inspectButton.disabled = true;
    progress.classList.add('is-running');
    results.classList.remove('is-visible');
    repair.classList.remove('is-visible');
    finding.setAttribute('aria-pressed', 'false');
    runSequence(inspectionSteps, (text) => { progressText.textContent = text; }, () => {
      progress.classList.remove('is-running');
      results.classList.add('is-visible');
      inspectButton.disabled = false;
      inspectButton.textContent = 'Run Inspection Again';
    });
  });

  finding.addEventListener('click', () => {
    finding.setAttribute('aria-pressed', 'true');
    repair.classList.add('is-visible');
    repair.scrollIntoView({ behavior: reducedMotion.matches ? 'auto' : 'smooth', block: 'nearest' });
  });

  previewButton.addEventListener('click', () => {
    previewButton.disabled = true;
    validation.classList.remove('is-complete');
    validation.querySelector('span').textContent = 'Comparing proposed structure…';
    const finishPreview = () => {
      validation.querySelector('span').textContent = 'Preview ready — no data has been changed';
      approveButton.disabled = false;
      previewButton.disabled = false;
    };
    reducedMotion.matches ? finishPreview() : window.setTimeout(finishPreview, 850);
  });

  approveButton.addEventListener('click', () => {
    approveButton.disabled = true;
    const approvalSteps = ['Repair validated', 'Provenance preserved', 'Review recorded', 'Simulation complete'];
    runSequence(approvalSteps, (text) => { validation.querySelector('span').textContent = text; }, () => {
      validation.classList.add('is-complete');
      approveButton.textContent = 'Simulation Approved';
    });
  });
}

const boundary = document.querySelector('[data-boundary]');
if (boundary) {
  const boundaryButton = boundary.querySelector('.boundary-trigger');
  const gate = boundary.querySelector('.approval-gate');
  const gateStatus = boundary.querySelector('.gate-status');
  boundaryButton.addEventListener('click', () => {
    boundaryButton.disabled = true;
    gateStatus.textContent = reducedMotion.matches ? 'Human approval required' : 'Preparing proposal…';
    const stopAtGate = () => {
      gateStatus.textContent = 'Human approval required';
      gate.classList.add('is-stopped');
      boundaryButton.textContent = 'Proposal stopped at gate';
    };
    reducedMotion.matches ? stopAtGate() : window.setTimeout(stopAtGate, 850);
  });
}

function setupSelectableTabs(selector, panelSelector, dataKey) {
  const tabs = [...document.querySelectorAll(selector)];
  const panel = document.querySelector(panelSelector);
  if (!tabs.length || !panel) return;

  const selectTab = (tab) => {
    tabs.forEach((item) => item.setAttribute('aria-selected', String(item === tab)));
    panel.querySelector('span').textContent = tab.textContent;
    panel.querySelector('p').textContent = tab.dataset[dataKey];
  };

  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => selectTab(tab));
    tab.addEventListener('keydown', (event) => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      let nextIndex = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : index + (event.key === 'ArrowRight' ? 1 : -1);
      nextIndex = (nextIndex + tabs.length) % tabs.length;
      tabs[nextIndex].focus();
      selectTab(tabs[nextIndex]);
    });
  });
}

setupSelectableTabs('.stage-list [role="tab"]', '.stage-explanation', 'stageDetail');
setupSelectableTabs('.timeline-tabs [role="tab"]', '.timeline-explanation', 'timelineDetail');

const lightbox = document.querySelector('.image-lightbox');
if (lightbox) {
  const lightboxImage = lightbox.querySelector('[data-lightbox-image]');
  const lightboxTitle = lightbox.querySelector('#lightbox-title');
  const lightboxCaption = lightbox.querySelector('#lightbox-caption');
  const closeButton = lightbox.querySelector('[data-lightbox-close]');
  let lightboxTrigger = null;

  document.querySelectorAll('.screenshot-trigger').forEach((trigger) => {
    trigger.addEventListener('click', () => {
      lightboxTrigger = trigger;
      const thumbnail = trigger.querySelector('img');
      lightboxImage.src = trigger.dataset.image;
      lightboxImage.alt = thumbnail.alt;
      lightboxTitle.textContent = trigger.dataset.title;
      lightboxCaption.textContent = trigger.dataset.caption;
      document.body.classList.add('lightbox-open');
      lightbox.showModal();
      closeButton.focus();
    });
  });

  const closeLightbox = () => {
    if (lightbox.open) lightbox.close();
  };

  closeButton.addEventListener('click', closeLightbox);
  lightbox.addEventListener('click', (event) => {
    if (event.target === lightbox) closeLightbox();
  });
  lightbox.addEventListener('cancel', () => {
    document.body.classList.remove('lightbox-open');
  });
  lightbox.addEventListener('close', () => {
    document.body.classList.remove('lightbox-open');
    lightboxImage.removeAttribute('src');
    if (lightboxTrigger) lightboxTrigger.focus();
  });
}

const corral = document.querySelector('[data-corral]');
if (corral) {
  const restraints = [...corral.querySelectorAll('input[name="restraint"]')];
  const countOutput = corral.querySelector('.selection-count');
  const promptInput = corral.querySelector('#corral-prompt');
  const runButton = corral.querySelector('.run-corral');
  const formMessage = corral.querySelector('.form-message');
  const results = corral.querySelector('.corral-results');
  const attemptOutput = corral.querySelector('.attempt-output');
  const attemptLabel = corral.querySelector('.attempt-label');
  const validationList = corral.querySelector('.validation-list');
  const decisionPanel = corral.querySelector('.decision-panel');
  const decisionKicker = corral.querySelector('.decision-kicker');
  const decisionTitle = corral.querySelector('.decision-title');
  const decisionCopy = corral.querySelector('.decision-copy');
  const score = corral.querySelector('.corral-score b');
  const retryButton = corral.querySelector('.retry-corral');
  const released = corral.querySelector('.released-response');
  const pathStages = [...corral.querySelectorAll('[data-path]')];
  const restraintNames = {
    max20: 'Maximum 20 words', max40: 'Maximum 40 words', noQuestions: 'No questions',
    noNumbers: 'No numbers', noE: 'No letter E', oneSentence: 'Exactly one sentence',
    includeSystem: 'Must include “system”', uncertainty: 'Must admit uncertainty'
  };
  const validators = {
    max20: (text) => countWords(text) <= 20,
    max40: (text) => countWords(text) <= 40,
    noQuestions: (text) => !text.includes('?'),
    noNumbers: (text) => !/[0-9]/.test(text),
    noE: (text) => !/e/i.test(text),
    oneSentence: (text) => ((text.match(/[.!?]+(?=\s|$)/g) || []).length === 1),
    includeSystem: (text) => /\bsystem\b/i.test(text),
    uncertainty: (text) => /\b(i['’]m not sure|i am not sure|uncertain|may|might)\b/i.test(text)
  };
  let attemptNumber = 0;

  function countWords(text) {
    return (text.trim().match(/\b[\w’'-]+\b/g) || []).length;
  }

  function selectedRules() {
    return restraints.filter((item) => item.checked).map((item) => item.value);
  }

  function updateSelection() {
    const count = selectedRules().length;
    countOutput.textContent = `${count} selected`;
    runButton.disabled = count < 2 || count > 4;
    formMessage.classList.toggle('is-error', count > 4);
    formMessage.textContent = count < 2 ? 'Choose at least two restraints to begin.' : count > 4 ? 'Choose no more than four restraints.' : 'The corral is ready.';
  }

  restraints.forEach((input) => {
    input.addEventListener('change', () => {
      if (input.checked && input.dataset.group) {
        restraints.filter((item) => item !== input && item.dataset.group === input.dataset.group).forEach((item) => { item.checked = false; });
      }
      updateSelection();
    });
  });

  corral.querySelectorAll('.sample-prompts button').forEach((button) => {
    button.addEventListener('click', () => {
      promptInput.value = button.textContent;
      promptInput.focus();
    });
  });

  function validate(text) {
    return selectedRules().map((rule) => ({ rule, passed: validators[rule](text) }));
  }

  function displayValidation(checks) {
    validationList.replaceChildren(...checks.map((check) => {
      const item = document.createElement('li');
      item.className = check.passed ? 'pass' : 'fail';
      item.textContent = restraintNames[check.rule];
      return item;
    }));
  }

  function setPath(activeIndex, finished = false) {
    pathStages.forEach((stage, index) => {
      stage.classList.toggle('is-active', !finished && index === activeIndex);
      stage.classList.toggle('is-complete', finished || index < activeIndex);
    });
  }

  function simulatedAttempt(isRetry) {
    if (isRetry) return selectedRules().includes('noE') ? 'I may fail, so strict guards limit risky output.' : 'This system may fail, so strict guards limit risky output.';
    const prompt = promptInput.value.toLowerCase();
    if (prompt.includes('pineapple')) return 'A flexible system may accept pineapple on pizza, but taste remains uncertain for every person.';
    if (prompt.includes('internet')) return 'The internet is a connected system that may move information quickly while amplifying both insight and error.';
    if (prompt.includes('artificial intelligence')) return 'Artificial intelligence is a system that may find patterns, generate output, and still make confident mistakes.';
    return 'A reliable system checks every AI answer before release, because model output may break important rules.';
  }

  function finishAttempt(text, isRetry) {
    const checks = validate(text);
    const failures = checks.filter((check) => !check.passed);
    attemptOutput.textContent = text;
    attemptLabel.textContent = `Attempt ${attemptNumber} of 2`;
    displayValidation(checks);
    results.classList.add('is-visible');
    decisionPanel.classList.toggle('is-fail', failures.length > 0);
    decisionPanel.classList.toggle('is-pass', failures.length === 0);
    released.classList.toggle('is-visible', failures.length === 0);
    retryButton.hidden = failures.length === 0 || attemptNumber >= 2;
    setPath(3, true);

    if (failures.length) {
      decisionKicker.textContent = 'AI bucked';
      decisionTitle.textContent = 'Response withheld';
      decisionCopy.textContent = `${failures.length} restraint${failures.length === 1 ? '' : 's'} violated. The simulated attempt was not released.`;
      score.textContent = '1';
      released.querySelector('p').textContent = '';
    } else {
      decisionKicker.textContent = isRetry ? 'Control restored' : 'Guardrails held';
      decisionTitle.textContent = 'Response released';
      decisionCopy.textContent = 'All selected restraints passed deterministic validation.';
      score.textContent = '1';
      released.querySelector('p').textContent = text;
    }
  }

  function runAttempt(isRetry = false) {
    attemptNumber = isRetry ? 2 : 1;
    const text = simulatedAttempt(isRetry);
    results.classList.remove('is-visible');
    released.classList.remove('is-visible');
    pathStages.forEach((stage) => stage.classList.remove('is-active', 'is-complete'));
    formMessage.textContent = isRetry ? 'Reining it back in…' : 'Prompt sent…';
    const steps = [0, 1, 2];
    let index = 0;
    setPath(steps[index]);

    const advance = () => {
      index += 1;
      if (index < steps.length) {
        setPath(steps[index]);
        formMessage.textContent = index === 1 ? 'Simulated attempt generated…' : 'Constraints checked.';
        window.setTimeout(advance, 320);
      } else {
        finishAttempt(text, isRetry);
        formMessage.textContent = 'Validation complete.';
      }
    };
    reducedMotion.matches ? finishAttempt(text, isRetry) : window.setTimeout(advance, 320);
  }

  corral.addEventListener('submit', (event) => {
    event.preventDefault();
    if (selectedRules().length < 2 || selectedRules().length > 4) return;
    if (!promptInput.value.trim()) promptInput.value = promptInput.placeholder;
    runAttempt(false);
  });
  retryButton.addEventListener('click', () => runAttempt(true));
  updateSelection();
}

const contactForm = document.querySelector('[data-contact-form]');
if (contactForm) {
  const contactStatus = contactForm.querySelector('.contact-status');
  const submitButton = contactForm.querySelector('.contact-submit');
  const defaultButtonLabel = submitButton.textContent;
  const fields = {
    name: contactForm.querySelector('#contact-name'),
    email: contactForm.querySelector('#contact-email'),
    reason: contactForm.querySelector('#contact-reason'),
    message: contactForm.querySelector('#contact-message')
  };
  const errors = {
    name: contactForm.querySelector('#name-error'),
    email: contactForm.querySelector('#email-error'),
    reason: contactForm.querySelector('#reason-error'),
    message: contactForm.querySelector('#message-error')
  };

  function setFieldError(key, message) {
    fields[key].setAttribute('aria-invalid', String(Boolean(message)));
    errors[key].textContent = message;
  }

  function setContactStatus(label, heading, message, isError = false) {
    const statusLabel = document.createElement('span');
    const statusHeading = document.createElement('h3');
    const statusMessage = document.createElement('p');
    statusLabel.textContent = label;
    statusHeading.textContent = heading;
    statusMessage.textContent = message;
    contactStatus.replaceChildren(statusLabel, statusHeading, statusMessage);
    contactStatus.classList.toggle('is-error', isError);
  }

  function validateContactField(key) {
    const value = fields[key].value.trim();
    let message = '';
    if (!value) {
      message = key === 'reason' ? 'Choose a reason for reaching out.' : `${key.charAt(0).toUpperCase() + key.slice(1)} is required.`;
    } else if (key === 'email' && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
      message = 'Enter a valid email address, such as name@example.com.';
    } else if (key === 'message' && value.length < 20) {
      message = `Add at least ${20 - value.length} more character${20 - value.length === 1 ? '' : 's'} to your message.`;
    }
    setFieldError(key, message);
    return !message;
  }

  Object.entries(fields).forEach(([key, field]) => {
    field.addEventListener(field.tagName === 'SELECT' ? 'change' : 'blur', () => validateContactField(key));
    field.addEventListener('input', () => {
      if (field.getAttribute('aria-invalid') === 'true') validateContactField(key);
      contactStatus.classList.remove('is-visible', 'is-error');
    });
  });

  contactForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    contactStatus.classList.remove('is-visible', 'is-error');
    const invalidKey = Object.keys(fields).find((key) => !validateContactField(key));
    Object.keys(fields).forEach((key) => validateContactField(key));
    if (invalidKey) {
      fields[invalidKey].focus();
      return;
    }

    submitButton.disabled = true;
    submitButton.textContent = 'Sending…';
    contactForm.setAttribute('aria-busy', 'true');

    try {
      const formData = new FormData(contactForm);
      const response = await fetch('/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(Object.fromEntries(formData.entries()))
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok || !result.ok) throw new Error(result.error || 'Your message could not be sent. Please try again.');

      setContactStatus('Message sent', 'Thanks for reaching out.', 'Your note is on its way to Greg.');
      contactForm.reset();
      Object.keys(fields).forEach((key) => setFieldError(key, ''));
    } catch (error) {
      setContactStatus('Message not sent', 'Please try again.', error.message, true);
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = defaultButtonLabel;
      contactForm.removeAttribute('aria-busy');
      contactStatus.classList.add('is-visible');
      contactStatus.focus();
    }
  });
}
