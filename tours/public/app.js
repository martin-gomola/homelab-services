const state = { tour: null, chapters: [], duration: 0 };
const $ = (selector) => document.querySelector(selector);
const audio = $('#audio');

function formatTime(seconds) {
  if (!Number.isFinite(seconds)) return '--:--';
  const whole = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(whole / 3600);
  const minutes = Math.floor((whole % 3600) / 60);
  const secs = String(whole % 60).padStart(2, '0');
  return hours ? `${hours}:${String(minutes).padStart(2, '0')}:${secs}` : `${minutes}:${secs}`;
}

function renderTour(tour) {
  state.tour = tour;
  state.chapters = tour.chapters;
  state.duration = tour.duration_seconds;
  document.title = `${tour.title} · Field Notes`;
  $('#show-name').textContent = tour.show_name;
  $('#title').textContent = tour.title;
  $('#summary').textContent = tour.summary;
  $('#duration').textContent = formatTime(tour.duration_seconds);
  $('#cover').src = tour.cover_url;
  $('#cover').alt = tour.cover_alt;
  $('#spotify-link').href = tour.spotify_url;
  $('#start-link').href = tour.starting_point_url;
  $('#route-frame').src = tour.route_url;
  $('#metadata').innerHTML = tour.metadata.map((value) => `<span class="pill">${value}</span>`).join('');
  $('#ticks').innerHTML = tour.chapters.map((chapter) => `<i style="left:${chapter.start_time_ms / (tour.duration_seconds * 10)}%"></i>`).join('');
  $('#chapters').innerHTML = tour.chapters.map((chapter, index) => `
    <button class="chapter" data-ms="${chapter.start_time_ms}">
      <span class="index">${String(index + 1).padStart(2, '0')}</span>
      <span>${chapter.title}</span>
      <span class="time">${formatTime(chapter.start_time_ms / 1000)}</span>
    </button>`).join('');
  audio.src = tour.audio_url;
  $('#toggle').disabled = false;
  $('#scrub').disabled = false;
  document.querySelectorAll('.chapter').forEach((row) => row.addEventListener('click', () => {
    audio.currentTime = Number(row.dataset.ms) / 1000;
    audio.play();
  }));
}

function syncPlayButton() {
  $('#toggle').textContent = audio.paused ? '▶' : '⏸';
  $('#toggle').ariaLabel = audio.paused ? 'Play' : 'Pause';
}

$('#toggle').addEventListener('click', () => audio.paused ? audio.play() : audio.pause());
audio.addEventListener('play', syncPlayButton);
audio.addEventListener('pause', syncPlayButton);
audio.addEventListener('ended', () => { audio.currentTime = 0; syncPlayButton(); });
audio.addEventListener('timeupdate', () => {
  const duration = audio.duration || state.duration;
  if (!duration) return;
  $('#scrub').value = audio.currentTime / duration;
  $('#now').textContent = formatTime(audio.currentTime);
  let active = 0;
  state.chapters.forEach((chapter, index) => { if (chapter.start_time_ms <= audio.currentTime * 1000) active = index; });
  document.querySelectorAll('.chapter').forEach((row, index) => row.classList.toggle('active', index === active));
});
$('#scrub').addEventListener('input', () => {
  const duration = audio.duration || state.duration;
  if (duration) audio.currentTime = Number($('#scrub').value) * duration;
});
document.querySelectorAll('.tab').forEach((tab) => tab.addEventListener('click', () => {
  document.querySelectorAll('.tab').forEach((item) => item.classList.toggle('active', item === tab));
  document.querySelectorAll('.panel').forEach((panel) => panel.classList.toggle('active', panel.id === tab.dataset.panel));
}));

fetch('/data/tours.json', { credentials: 'same-origin', cache: 'no-store' })
  .then((response) => { if (!response.ok) throw new Error(`Tour catalog returned ${response.status}`); return response.json(); })
  .then((catalog) => {
    const slug = location.pathname.split('/').filter(Boolean)[0] || catalog.default_tour;
    const tour = catalog.tours.find((item) => item.slug === slug) || catalog.tours.find((item) => item.slug === catalog.default_tour);
    if (!tour) throw new Error('No tour is configured');
    renderTour(tour);
  })
  .catch((error) => { $('#title').textContent = 'Tour unavailable'; $('#summary').innerHTML = `<span class="error">${error.message}</span>`; });
