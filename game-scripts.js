// Game page interactive features

document.addEventListener('DOMContentLoaded', () => {
  setupCarousel();
  setupWishlistButton();
  setupActionButton();
});

// Carousel functionality
function setupCarousel() {
  const prevBtn = document.querySelector('.carousel-nav.prev');
  const nextBtn = document.querySelector('.carousel-nav.next');
  const track = document.querySelector('.carousel-track');

  if (!prevBtn || !nextBtn || !track) return;

  const scrollAmount = 220; // item width (200px) + gap (20px)

  prevBtn.addEventListener('click', () => {
    track.scrollBy({
      left: -scrollAmount,
      behavior: 'smooth'
    });
  });

  nextBtn.addEventListener('click', () => {
    track.scrollBy({
      left: scrollAmount,
      behavior: 'smooth'
    });
  });

  // Update button visibility based on scroll position
  updateCarouselButtons();
  track.addEventListener('scroll', updateCarouselButtons);

  function updateCarouselButtons() {
    const isAtStart = track.scrollLeft === 0;
    const isAtEnd = track.scrollLeft >= track.scrollWidth - track.clientWidth - 10;

    prevBtn.style.opacity = isAtStart ? '0.5' : '1';
    prevBtn.style.pointerEvents = isAtStart ? 'none' : 'auto';
    nextBtn.style.opacity = isAtEnd ? '0.5' : '1';
    nextBtn.style.pointerEvents = isAtEnd ? 'none' : 'auto';
  }
}

// Wishlist button
function setupWishlistButton() {
  const wishlistBtn = document.querySelector('.wishlist-btn');
  if (!wishlistBtn) return;

  wishlistBtn.addEventListener('click', (e) => {
    e.preventDefault();
    const isWishlisted = wishlistBtn.classList.toggle('wishlisted');
    
    // Update button appearance
    if (isWishlisted) {
      wishlistBtn.innerHTML = '❤️ Wishlisted';
      wishlistBtn.style.background = 'rgba(244, 63, 94, 0.15)';
      wishlistBtn.style.borderColor = 'rgba(244, 63, 94, 0.3)';
      wishlistBtn.style.color = '#f43f5e';
    } else {
      wishlistBtn.innerHTML = '♡ Wishlist';
      wishlistBtn.style.background = 'rgba(255, 255, 255, 0.06)';
      wishlistBtn.style.borderColor = 'rgba(255, 255, 255, 0.12)';
      wishlistBtn.style.color = 'rgba(229, 231, 235, 0.95)';
    }
  });
}

// Action button
function setupActionButton() {
  const actionBtn = document.querySelector('.action-btn');
  if (!actionBtn) return;

  actionBtn.addEventListener('click', (e) => {
    e.preventDefault();
    alert('Game download started! (Demo functionality)');
  });
}

// Handle carousel item clicks for preview
document.addEventListener('click', (e) => {
  if (e.target.closest('.carousel-item')) {
    const img = e.target.closest('.carousel-item img');
    if (img) {
      console.log('Video preview clicked:', img.alt);
      // Could expand to larger preview modal here
    }
  }
});
