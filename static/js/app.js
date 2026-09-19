document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.flash').forEach((el) => {
    setTimeout(() => { el.classList.add('hide'); }, 4500);
  });
  document.querySelectorAll('video').forEach((video) => {
    video.addEventListener('error', () => {
      const box = video.closest('.video-shell');
      if (box) {
        const note = document.createElement('div');
        note.className = 'video-note';
        note.textContent = 'پخش این لینک در مرورگر فعلی در دسترس نیست. لینک مستقیم MP4/HLS را بررسی کنید.';
        box.appendChild(note);
      }
    });
  });
});
