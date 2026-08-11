// Mobile nav toggle
const burger = document.getElementById('burgerBtn');
const nav = document.getElementById('mainNav');
burger?.addEventListener('click', () => {
  nav.classList.toggle('is-open');
});

// Mega menu toggle on mobile (click)
document.querySelectorAll('.qntc-nav__item.has-mega > .qntc-nav__link').forEach(btn => {
  btn.addEventListener('click', (e) => {
    if (window.innerWidth <= 860) {
      e.preventDefault();
      const item = btn.closest('.qntc-nav__item');
      document.querySelectorAll('.qntc-nav__item.has-mega').forEach(i => {
        if (i !== item) i.classList.remove('is-open');
      });
      item.classList.toggle('is-open');
    }
  });
});

// Search overlay
const searchBtn = document.getElementById('searchBtn');
const searchOverlay = document.getElementById('searchOverlay');
const searchClose = document.getElementById('searchClose');
searchBtn?.addEventListener('click', () => searchOverlay.classList.add('is-open'));
searchClose?.addEventListener('click', () => searchOverlay.classList.remove('is-open'));
searchOverlay?.addEventListener('click', (e) => {
  if (e.target === searchOverlay) searchOverlay.classList.remove('is-open');
});

// Share button
document.getElementById('shareBtn')?.addEventListener('click', async () => {
  const shareData = { title: 'مهرجان قطر الدولي للأغذية', url: location.href };
  try {
    if (navigator.share) await navigator.share(shareData);
    else { await navigator.clipboard.writeText(location.href); alert('تم نسخ الرابط'); }
  } catch (e) {}
});

// Gallery slider
const track = document.getElementById('galleryTrack');
const dotsContainer = document.getElementById('galleryDots');
if (track && dotsContainer) {
  const slides = track.querySelectorAll('.gallery__slide');
  let current = 0;
  slides.forEach((_, i) => {
    const dot = document.createElement('button');
    if (i === 0) dot.classList.add('is-active');
    dot.addEventListener('click', () => goTo(i));
    dotsContainer.appendChild(dot);
  });
  const dots = dotsContainer.querySelectorAll('button');

  function goTo(i) {
    current = (i + slides.length) % slides.length;
    track.style.transform = `translateX(${current * 100}%)`;
    dots.forEach((d, idx) => d.classList.toggle('is-active', idx === current));
  }
  document.getElementById('galleryNext')?.addEventListener('click', () => goTo(current - 1));
  document.getElementById('galleryPrev')?.addEventListener('click', () => goTo(current + 1));

  // autoplay
  let timer = setInterval(() => goTo(current + 1), 5000);
  const slider = document.getElementById('gallerySlider');
  slider?.addEventListener('mouseenter', () => clearInterval(timer));
  slider?.addEventListener('mouseleave', () => timer = setInterval(() => goTo(current + 1), 5000));

  // swipe
  let startX = 0;
  track.addEventListener('touchstart', e => startX = e.touches[0].clientX, {passive:true});
  track.addEventListener('touchend', e => {
    const diff = e.changedTouches[0].clientX - startX;
    if (Math.abs(diff) > 50) goTo(current + (diff > 0 ? -1 : 1));
  });
}

// Form submit -> POST /api/register (saves to DB + sends email)
document.getElementById('regForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;
  const submitBtn = form.querySelector('.reg-submit');
  const success = document.getElementById('formSuccess');
  const originalText = submitBtn.textContent;
  submitBtn.disabled = true;
  submitBtn.textContent = 'جاري الإرسال...';

  const formData = new FormData(form);
  try {
    const resp = await fetch('/api/register', { method: 'POST', body: formData });
    const data = await resp.json();
    if (data.ok) {
      if (success) {
        const note = data.email_sent
          ? 'تم استلام طلبك بنجاح. تم إرسال بريد التأكيد إلى عنوانك.'
          : 'تم استلام طلبك بنجاح. (تعذّر إرسال بريد التأكيد تلقائياً، سنتواصل معك قريباً)';
        success.textContent = note;
        success.hidden = false;
      }
      form.reset();
      document.querySelectorAll('.file-upload__preview.is-shown').forEach(p => p.classList.remove('is-shown'));
      form.scrollIntoView({ behavior: 'smooth', block: 'center' });
      setTimeout(() => { if (success) success.hidden = true; }, 6000);
    } else {
      alert('حدث خطأ: ' + (data.error || 'تعذر إرسال الطلب'));
    }
  } catch (err) {
    alert('تعذر الاتصال بالخادم: ' + err);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = originalText;
  }
});

// Contact form submit -> POST /api/contact (sends a copy to the festival team)
document.getElementById('contactForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = e.target;
  const submitBtn = form.querySelector('.reg-submit');
  const success = document.getElementById('contactSuccess');
  if (!form.reportValidity()) return;
  const originalText = submitBtn.textContent;
  submitBtn.disabled = true;
  submitBtn.textContent = 'جاري الإرسال...';

  try {
    const resp = await fetch('/api/contact', { method: 'POST', body: new FormData(form) });
    const data = await resp.json();
    if (!data.ok) throw new Error(data.error || 'تعذر إرسال الرسالة');
    form.reset();
    if (success) success.hidden = false;
  } catch (err) {
    alert(err.message || 'تعذر الاتصال بالخادم');
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = originalText;
  }
});

// Cookie consent
const cookie = document.getElementById('cookie');
if (cookie && !localStorage.getItem('cookieConsent')) {
  document.getElementById('cookieAcceptAll')?.addEventListener('click', () => {
    localStorage.setItem('cookieConsent', 'all');
    cookie.classList.add('is-hidden');
  });
  document.getElementById('cookieAcceptNecessary')?.addEventListener('click', () => {
    localStorage.setItem('cookieConsent', 'necessary');
    cookie.classList.add('is-hidden');
  });
} else if (cookie) {
  cookie.classList.add('is-hidden');
}

// File upload preview: show filename + accept/reject icon
const OK_SVG = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M5 12l5 5 9-10" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
const ERR_SVG = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/></svg>';
const MAX_BYTES = 10 * 1024 * 1024;

document.querySelectorAll('input[type="file"]').forEach(input => {
  input.addEventListener('change', () => {
    const preview = input.closest('.form-field')?.querySelector('.file-upload__preview');
    if (!preview) return;
    const nameEl = preview.querySelector('.file-upload__preview-name');
    const iconEl = preview.querySelector('.file-upload__preview-icon');

    if (!input.files || !input.files[0]) {
      preview.classList.remove('is-shown');
      return;
    }
    const file = input.files[0];
    const allowed = (input.getAttribute('accept') || '').split(',').map(s => s.trim().toLowerCase());
    const ext = '.' + (file.name.split('.').pop() || '').toLowerCase();
    const extOk = !allowed.length || allowed.includes(ext);
    const sizeOk = file.size <= MAX_BYTES;
    const accepted = extOk && sizeOk;

    nameEl.textContent = file.name;
    iconEl.innerHTML = accepted ? OK_SVG : ERR_SVG;
    iconEl.classList.toggle('is-ok', accepted);
    iconEl.classList.toggle('is-err', !accepted);
    preview.classList.add('is-shown');
  });
});

// Back to top
const backToTop = document.querySelector('.back-to-top');
window.addEventListener('scroll', () => {
  backToTop?.classList.toggle('is-visible', window.scrollY > 400);
});

// Sticky header shadow on scroll
const header = document.querySelector('.qntc-header');
window.addEventListener('scroll', () => {
  if (header) header.style.boxShadow = window.scrollY > 10 ? '0 4px 16px rgba(0,0,0,.08)' : '0 2px 8px rgba(0,0,0,.04)';
});
