// App banner close
document.getElementById('appBannerClose')?.addEventListener('click', () => {
  document.getElementById('appBanner').style.display = 'none';
});

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
          : 'تم استلام طلبك بنجاح. (سيصلك بريد التأكيد قريباً)';
        success.textContent = note;
        success.hidden = false;
      }
      form.reset();
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
