const API_BASE = 'http://127.0.0.1:8000';
const state = { request: null, bookings: JSON.parse(localStorage.getItem('sahaayak-bookings') || '[]'), map: null, marker: null, matchMap: null, addressTimer: null };
const $ = (id) => document.getElementById(id);
let registerMode = false;
let resetToken = '';

function setAuthenticatedUser(user) {
  $('user-name').textContent = user.full_name;
  $('user-avatar').textContent = user.full_name.split(' ').map((part) => part[0]).join('').slice(0, 2).toUpperCase();
  $('auth-gate').classList.add('hidden');
}
function setAuthError(message) { $('auth-error').textContent = message; }
async function loadSession() {
  const token = localStorage.getItem('sahaayak-token');
  if (!token) return;
  try {
    const response = await fetch(`${API_BASE}/auth/me`, { headers: { Authorization: `Bearer ${token}` } });
    if (!response.ok) throw new Error();
    setAuthenticatedUser(await response.json());
  } catch { localStorage.removeItem('sahaayak-token'); }
}
function openAuthMode(mode) {
  registerMode = mode === 'register';
  $('auth-choice').classList.add('hidden');
  $('auth-form').classList.remove('hidden');
  $('forgot-form').classList.add('hidden');
  document.querySelectorAll('.registration-only').forEach((field) => field.classList.toggle('hidden', !registerMode));
  $('auth-name').required = registerMode;
  $('auth-title').textContent = registerMode ? 'Create your account' : 'Welcome back';
  $('auth-copy').textContent = registerMode ? 'Create your account to book trusted cooperative services.' : 'Sign in to request trusted cooperative services near you.';
  $('auth-submit-label').textContent = registerMode ? 'Create account' : 'Sign in';
  setAuthError('');
}
document.querySelectorAll('[data-auth-choice]').forEach((button) => button.addEventListener('click', () => openAuthMode(button.dataset.authChoice)));
$('auth-mode').addEventListener('click', () => {
  $('auth-choice').classList.remove('hidden');
  $('auth-form').classList.add('hidden');
  $('forgot-form').classList.add('hidden');
  $('auth-worker-fields').classList.add('hidden');
  $('auth-worker').checked = false;
  setAuthError('');
});
$('forgot-link').addEventListener('click', () => {
  $('auth-form').classList.add('hidden');
  $('auth-choice').classList.add('hidden');
  $('auth-mode').classList.remove('hidden');
  $('forgot-form').classList.remove('hidden');
  $('auth-title').textContent = 'Reset your password';
  $('auth-copy').textContent = 'Enter your account email to start a secure password reset.';
  $('forgot-error').textContent = '';
});
$('forgot-form').addEventListener('submit', async (event) => {
  event.preventDefault(); $('forgot-error').textContent = '';
  try {
    if (!resetToken) {
      const response = await fetch(`${API_BASE}/auth/forgot-password`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: $('forgot-email').value }) });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Could not start password reset');
      resetToken = data.reset_token;
      $('new-password-field').classList.remove('hidden'); $('new-password').required = true;
      $('forgot-help').textContent = 'Reset token received. Choose a new password now.';
      $('forgot-submit-label').textContent = 'Update password';
      return;
    }
    const response = await fetch(`${API_BASE}/auth/reset-password`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token: resetToken, new_password: $('new-password').value }) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Could not reset password');
    resetToken = ''; $('forgot-form').classList.add('hidden'); $('auth-form').classList.remove('hidden'); openAuthMode('login'); setAuthError('Password updated. You can now sign in.');
  } catch (error) { $('forgot-error').textContent = error.message; }
});
$('auth-worker').addEventListener('change', () => $('auth-worker-fields').classList.toggle('hidden', !$('auth-worker').checked));
$('auth-form').addEventListener('submit', async (event) => {
  event.preventDefault(); setAuthError('');
  try {
    let response;
    if (registerMode) {
      const worker = $('auth-worker').checked;
      response = await fetch(`${API_BASE}/auth/register`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ full_name: $('auth-name').value, email: $('auth-email').value, password: $('auth-password').value, phone: $('auth-phone').value, aadhaar_number: $('auth-aadhaar').value, role: worker ? 'provider' : 'customer', upi_id: worker ? $('auth-upi').value : null, bank_account_number: worker ? $('auth-bank-account').value : null, bank_ifsc: worker ? $('auth-ifsc').value : null, permanent_address: worker ? $('auth-permanent-address').value : null, residential_address: worker ? $('auth-residential-address').value : null }) });
      if (!response.ok) throw new Error((await response.json()).detail || 'Could not create account');
      $('auth-mode').click();
    }
    const form = new URLSearchParams({ username: $('auth-email').value, password: $('auth-password').value });
    response = await fetch(`${API_BASE}/auth/login`, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: form });
    if (!response.ok) throw new Error((await response.json()).detail || 'Incorrect email or password');
    const token = await response.json(); localStorage.setItem('sahaayak-token', token.access_token);
    const me = await fetch(`${API_BASE}/auth/me`, { headers: { Authorization: `Bearer ${token.access_token}` } });
    setAuthenticatedUser(await me.json());
  } catch (error) { setAuthError(error.message || 'Authentication failed. Start the backend and try again.'); }
});
$('logout').addEventListener('click', () => { localStorage.removeItem('sahaayak-token'); location.reload(); });
loadSession();
const today = new Date();
$('date').min = today.toISOString().split('T')[0];
$('date').value = today.toISOString().split('T')[0];

function showToast(message) { const toast = $('toast'); toast.textContent = message; toast.classList.add('show'); setTimeout(() => toast.classList.remove('show'), 3000); }
function showScreen(name) {
  document.querySelectorAll('.screen').forEach((screen) => screen.classList.toggle('active-screen', screen.id === `${name}-screen`));
  document.querySelectorAll('.nav-item').forEach((item) => item.classList.toggle('active', item.dataset.screen === name));
  $('page-title').textContent = name === 'request' ? 'Start with your need' : name === 'matches' ? 'Nearby workers' : 'My bookings';
  if (name === 'bookings') renderBookings();
  if (name === 'matches' && state.request) setTimeout(() => state.matchMap?.invalidateSize(), 100);
}
document.querySelectorAll('[data-screen]').forEach((button) => button.addEventListener('click', () => showScreen(button.dataset.screen)));
document.querySelectorAll('[data-need]').forEach((button) => button.addEventListener('click', () => { $('need').value = button.dataset.need; }));

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognition) {
  const recognition = new SpeechRecognition();
  recognition.continuous = false;
  recognition.interimResults = false;
  recognition.lang = 'en-US';
  recognition.maxAlternatives = 1;
  let voiceActive = false;
  recognition.onstart = () => { $('voice-input').classList.add('listening'); $('voice-status').textContent = 'Listening...'; };
  recognition.onresult = (event) => { $('need').value = event.results[0][0].transcript; $('voice-status').textContent = 'Voice added. You can edit it before continuing.'; voiceActive = false; };
  recognition.onerror = (event) => {
    const messages = { 'not-allowed': 'Microphone access is blocked. Allow microphone access for this site, then try again.', 'service-not-allowed': 'Speech recognition is blocked by this browser. Try Chrome or Edge.', 'no-speech': 'I did not hear anything. Please try again and speak clearly.', network: 'Speech recognition needs an internet connection. Please try again.' };
    voiceActive = false; $('voice-input').classList.remove('listening');
    if (event.error !== 'aborted') $('voice-status').textContent = event.error === 'network' && !navigator.onLine ? 'You are offline. Reconnect to the internet, then press the microphone again.' : messages[event.error] || 'Voice input could not start. Press the microphone to try again or type your request.';
  };
  recognition.onend = () => { voiceActive = false; $('voice-input').classList.remove('listening'); };
  $('voice-input').addEventListener('click', async () => {
    if (voiceActive) { recognition.stop(); return; }
    if (!navigator.onLine) { $('voice-status').textContent = 'You are offline. Reconnect to the internet, then press the microphone again.'; return; }
    try {
      if (navigator.mediaDevices?.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach((track) => track.stop());
      }
      voiceActive = true; $('voice-status').textContent = 'Starting microphone...'; recognition.start();
    } catch (error) {
      voiceActive = false;
      $('voice-status').textContent = error.name === 'NotAllowedError' ? 'Microphone access is blocked. Allow it in the browser address bar, then try again.' : 'Voice input could not start. Please try again or type your request.';
    }
  });
} else {
  $('voice-input').addEventListener('click', () => { $('voice-status').textContent = 'Voice input needs Chrome or Edge. Please type your request or open this page in a supported browser.'; });
}

function updatePin(lat, lng) {
  $('latitude').value = lat.toFixed(6); $('longitude').value = lng.toFixed(6);
  if (state.marker) state.marker.setLatLng([lat, lng]);
}
async function reverseGeocode(lat, lng) {
  try {
    const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}`);
    if (!response.ok) return;
    const data = await response.json();
    if (data.display_name) $('address').value = data.display_name;
  } catch { /* The map remains usable when geocoding is unavailable. */ }
}
function initializeMap() {
  const defaultLocation = [17.385, 78.4867];
  state.map = L.map('map').setView(defaultLocation, 13);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap contributors' }).addTo(state.map);
  state.marker = L.marker(defaultLocation, { draggable: true }).addTo(state.map);
  updatePin(...defaultLocation);
  state.marker.on('dragend', () => { const point = state.marker.getLatLng(); updatePin(point.lat, point.lng); reverseGeocode(point.lat, point.lng); });
  state.map.on('click', (event) => { updatePin(event.latlng.lat, event.latlng.lng); reverseGeocode(event.latlng.lat, event.latlng.lng); });
}
initializeMap();
$('locate').addEventListener('click', () => {
  if (!navigator.geolocation) return showToast('Location is not available in this browser.');
  navigator.geolocation.getCurrentPosition((position) => { const { latitude, longitude } = position.coords; state.map.setView([latitude, longitude], 16); updatePin(latitude, longitude); reverseGeocode(latitude, longitude); showToast('Current location pinned.'); }, () => showToast('Please allow location access or move the pin manually.'));
});
function useCurrentLocation() {
  if (!navigator.geolocation) return showToast('Location is not available in this browser.');
  navigator.geolocation.getCurrentPosition((position) => {
    const { latitude, longitude } = position.coords;
    updatePin(latitude, longitude);
    if (state.request) state.request = { ...state.request, latitude, longitude };
    state.map?.setView([latitude, longitude], 16);
    state.matchMap?.setView([latitude, longitude], 16);
    reverseGeocode(latitude, longitude).then(() => {
      if (state.request) { state.request.address = $('address').value; $('selected-address').textContent = state.request.address; }
    });
    showToast('Booking location updated.');
  }, () => showToast('Please allow location access or move the pin manually.'));
}
$('booking-locate').addEventListener('click', useCurrentLocation);
$('open-google-maps').addEventListener('click', () => {
  const openMap = (latitude, longitude) => {
    $('live-location-map').src = `https://www.google.com/maps?q=${latitude},${longitude}&output=embed`;
    $('live-map-status').textContent = 'Live position';
    window.open(`https://www.google.com/maps?q=${latitude},${longitude}`, '_blank', 'noopener,noreferrer');
  };
  if (!navigator.geolocation) return showToast('Location is not available in this browser.');
  navigator.geolocation.getCurrentPosition((position) => openMap(position.coords.latitude, position.coords.longitude), () => showToast('Please allow location access to open Google Maps.'));
});
$('address').addEventListener('input', () => {
  clearTimeout(state.addressTimer);
  const query = $('address').value.trim();
  if (query.length < 3) { $('address-suggestions').innerHTML = ''; return; }
  state.addressTimer = setTimeout(async () => {
    try {
      const response = await fetch(`https://nominatim.openstreetmap.org/search?format=jsonv2&limit=5&countrycodes=in&q=${encodeURIComponent(query)}`);
      const results = response.ok ? await response.json() : [];
      $('address-suggestions').innerHTML = results.map((result) => `<button type="button" data-lat="${result.lat}" data-lon="${result.lon}">${result.display_name}</button>`).join('');
      document.querySelectorAll('#address-suggestions button').forEach((button) => button.addEventListener('click', () => {
        const lat = Number(button.dataset.lat); const lng = Number(button.dataset.lon);
        $('address').value = button.textContent; updatePin(lat, lng); state.map.setView([lat, lng], 16); $('address-suggestions').innerHTML = '';
      }));
    } catch { $('address-suggestions').innerHTML = ''; }
  }, 350);
});
$('address').addEventListener('blur', () => setTimeout(() => { $('address-suggestions').innerHTML = ''; }, 180));

$('request-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  state.request = { need: $('need').value, date: $('date').value, time: $('time').value, approver: $('approver').value, address: $('address').value, latitude: Number($('latitude').value), longitude: Number($('longitude').value) };
  $('request-summary').textContent = `${state.request.need} · ${state.request.date} · ${state.request.time}`;
  $('selected-address').textContent = state.request.address;
  $('selected-approver').textContent = state.request.approver;
  $('selected-time').textContent = `${state.request.date} · ${state.request.time}`;
  renderMatches();
  showScreen('matches');
});

function renderMatches() {
  const need = state.request.need.toLowerCase();
  const category = need.includes('plumb') ? 'Plumbing' : need.includes('elect') ? 'Electrical' : need.includes('clean') ? 'Cleaning' : need.includes('carp') ? 'Carpentry' : need.includes('cater') ? 'Catering' : need.includes('mechanic') || need.includes('car ') ? 'Car mechanic' : need.includes('cook') ? 'Cook' : need.includes('doctor') || need.includes('medical') ? 'Doctor' : need.includes('nurs') ? 'Nursing' : need.includes('luggage') || need.includes('shift') ? 'Luggage shifting' : need.includes('driver') ? 'Driver' : need.includes('garden') ? 'Gardening' : 'General services';
  const workers = [{ name: 'Suresh Kumar', initials: 'SK', society: 'Hyderabad Labour Cooperative Society', skill: category, experience: '12 years experience', rate: 350, color: '#f3d0ad' }, { name: 'Meena Devi', initials: 'MD', society: 'Sakhi Workers Cooperative', skill: category, experience: '8 years experience', rate: 300, color: '#c4dcef' }, { name: 'Rafiq Ahmed', initials: 'RA', society: 'City Services Labour Federation', skill: category, experience: '10 years experience', rate: 325, color: '#d6e6a2' }];
  $('worker-list').innerHTML = workers.map((worker) => `<article class="worker-card"><span class="worker-avatar" style="background:${worker.color}">${worker.initials}</span><div><h3>${worker.name}</h3><p>${worker.society}</p><span class="verified">✓ Verified · ${worker.skill} · ${worker.experience}</span></div><div class="rate"><strong>₹${worker.rate}</strong><small>per hour</small><button class="select-worker" data-worker="${worker.name}" data-rate="${worker.rate}">Select worker</button></div></article>`).join('');
  document.querySelectorAll('.select-worker').forEach((button) => button.addEventListener('click', () => confirmBooking(button.dataset.worker, Number(button.dataset.rate))));
  if (!state.matchMap) { state.matchMap = L.map('match-map', { zoomControl: false }).setView([state.request.latitude, state.request.longitude], 14); L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap contributors' }).addTo(state.matchMap); } else state.matchMap.setView([state.request.latitude, state.request.longitude], 14);
  L.marker([state.request.latitude, state.request.longitude]).addTo(state.matchMap).bindPopup('Your service location').openPopup();
}

function confirmBooking(worker, rate) {
  const booking = { id: Date.now(), need: state.request.need, worker, rate, ...state.request, status: 'Request sent' };
  state.bookings.unshift(booking); localStorage.setItem('sahaayak-bookings', JSON.stringify(state.bookings));
  showToast(`Request sent to ${worker}.`); showScreen('bookings');
}
async function cancelBooking(id) {
  const booking = state.bookings.find((item) => item.id === id);
  if (!booking || booking.status === 'Cancelled') return;
  if (!confirm('Cancel this service request?')) return;
  const token = localStorage.getItem('sahaayak-token');
  if (token && Number.isInteger(id)) {
    try {
      await fetch(`${API_BASE}/bookings/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify({ status: 'cancelled' }) });
    } catch { /* Keep the local booking state responsive if the API is unavailable. */ }
  }
  booking.status = 'Cancelled';
  localStorage.setItem('sahaayak-bookings', JSON.stringify(state.bookings));
  renderBookings();
  showToast('Your service request was cancelled.');
}
function renderBookings() {
  if (!state.bookings.length) { $('booking-list').innerHTML = '<div class="empty-state"><span>◷</span><h3>No bookings yet</h3><p>Start with a service request and your confirmed jobs will appear here.</p></div>'; return; }
  $('booking-list').innerHTML = state.bookings.map((booking) => `<article class="booking-item"><div><h3>${booking.need}</h3><p>${booking.date} · ${booking.time} · ${booking.address}</p><p>Approver: ${booking.approver} · Worker: ${booking.worker}</p></div><div class="booking-actions"><span class="status ${booking.status === 'Cancelled' ? 'status-cancelled' : ''}">${booking.status}</span>${booking.status !== 'Cancelled' ? `<button class="cancel-button" data-cancel="${booking.id}">Cancel request</button>` : ''}</div></article>`).join('');
  document.querySelectorAll('[data-cancel]').forEach((button) => button.addEventListener('click', () => cancelBooking(Number(button.dataset.cancel))));
}

const yoyoAnswers = [
  { words: ['book', 'request', 'service'], answer: 'I can help you book that. Choose a service, select a date and time, enter the contact name and address, then select a verified worker. Your request will appear under **My bookings**.' },
  { words: ['location', 'map', 'address', 'current', 'direction'], answer: 'For the service address, start typing to see suggestions. You can choose one, press **Use my location**, click the map, or drag the pin. The same location control is available while reviewing your booking.' },
  { words: ['cancel'], answer: 'To cancel a request, open **My bookings** and choose **Cancel request** on an active booking. The updated status will remain visible for your records.' },
  { words: ['worker', 'verified', 'provider'], answer: 'You will see verified cooperative workers with their society, skill, experience, and hourly rate before choosing one. This helps you compare options clearly.' },
  { words: ['pay', 'payment', 'price', 'cost', 'rate'], answer: 'The worker’s hourly rate is shown before booking. The final amount depends on the selected duration, and emergency requests may include an emergency charge.' },
  { words: ['emergency', 'urgent'], answer: 'For urgent help, describe the situation in your service request and choose the earliest available time. The platform supports emergency booking requests.' },
  { words: ['hello', 'hi', 'hey', 'good morning', 'good evening'], answer: 'Hello! I’m YOYO, your friendly CONNECTX assistant. What service or booking question can I help you with today?' },
  { words: ['thank', 'thanks'], answer: 'You’re very welcome. I’m here whenever you need help with CONNECTX.' },
  { words: ['help', 'what', 'yoyo'], answer: 'I can explain booking, worker selection, pricing, address entry, location sharing, emergency requests, and cancellations. Ask me naturally and I’ll guide you step by step.' }
];
function formatYoyoText(text) { return text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>'); }
function yoyoReply(message) {
  const normalized = message.toLowerCase();
  const match = yoyoAnswers.find((item) => item.words.some((word) => normalized.includes(word)));
  return match ? match.answer : 'That is a good question. I do not have that detail yet, but I can help with booking a service, finding a worker, entering an address, sharing your location, pricing, emergency requests, or cancelling a booking. Could you tell me a little more?';
}
function addYoyoMessage(text, type, save = true) {
  const message = document.createElement('div'); message.className = `yoyo-message ${type}`;
  if (type === 'bot') message.innerHTML = formatYoyoText(text); else message.textContent = text;
  $('yoyo-messages').appendChild(message); $('yoyo-messages').scrollTop = $('yoyo-messages').scrollHeight;
  if (save) { const history = JSON.parse(localStorage.getItem('connectx-yoyo-chat') || '[]'); history.push({ text, type }); localStorage.setItem('connectx-yoyo-chat', JSON.stringify(history.slice(-40))); }
}
function loadYoyoChat() {
  const history = JSON.parse(localStorage.getItem('connectx-yoyo-chat') || '[]');
  if (history.length) history.forEach((item) => addYoyoMessage(item.text, item.type, false));
  else addYoyoMessage('Hi, I’m YOYO. I’m here to help with services, locations, bookings, and using this page. What would you like to know?', 'bot');
}
function askYoyo(message) { addYoyoMessage(message, 'user'); const typing = document.createElement('div'); typing.className = 'yoyo-message bot yoyo-typing'; typing.textContent = 'YOYO is thinking...'; $('yoyo-messages').appendChild(typing); setTimeout(() => { typing.remove(); addYoyoMessage(yoyoReply(message), 'bot'); }, 450); }
loadYoyoChat();
$('yoyo-launcher').addEventListener('click', () => { if (yoyoMoved) { yoyoMoved = false; return; } $('yoyo-panel').classList.add('open'); $('yoyo-panel').setAttribute('aria-hidden', 'false'); $('yoyo-input').focus(); });
$('yoyo-close').addEventListener('click', () => { $('yoyo-panel').classList.remove('open'); $('yoyo-panel').setAttribute('aria-hidden', 'true'); });
$('yoyo-form').addEventListener('submit', (event) => { event.preventDefault(); const input = $('yoyo-input'); const message = input.value.trim(); if (!message) return; input.value = ''; askYoyo(message); });
document.querySelectorAll('[data-yoyo-prompt]').forEach((button) => button.addEventListener('click', () => askYoyo(button.dataset.yoyoPrompt)));
let yoyoDragging = false;
let yoyoMoved = false;
let yoyoStartX = 0;
let yoyoStartY = 0;
$('yoyo-launcher').addEventListener('pointerdown', (event) => {
  yoyoDragging = true; yoyoMoved = false; yoyoStartX = event.clientX; yoyoStartY = event.clientY;
  $('yoyo-launcher').setPointerCapture(event.pointerId);
});
$('yoyo-launcher').addEventListener('pointermove', (event) => {
  if (!yoyoDragging) return;
  const deltaX = event.clientX - yoyoStartX; const deltaY = event.clientY - yoyoStartY;
  if (Math.abs(deltaX) < 4 && Math.abs(deltaY) < 4) return;
  yoyoMoved = true;
  const widget = $('yoyo-widget'); const bounds = widget.getBoundingClientRect();
  widget.style.left = `${Math.max(8, Math.min(window.innerWidth - bounds.width - 8, bounds.left + deltaX))}px`;
  widget.style.top = `${Math.max(8, Math.min(window.innerHeight - $('yoyo-launcher').offsetHeight - 8, bounds.top + deltaY))}px`;
  widget.style.right = 'auto'; widget.style.bottom = 'auto';
  yoyoStartX = event.clientX; yoyoStartY = event.clientY;
});
$('yoyo-launcher').addEventListener('pointerup', () => { yoyoDragging = false; });
$('yoyo-launcher').addEventListener('click', (event) => { if (yoyoMoved) { event.preventDefault(); event.stopImmediatePropagation(); yoyoMoved = false; } });
