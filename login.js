const ADMIN_EMAIL = 'admin@starboundgamelabs.com','llyrowen@starboundgamelabs.com';
const ADMIN_PASSWORD = 'StarboundL1Y4!','LlyrOwen5597!';

function loginAdmin(email, password) {
  if (email === ADMIN_EMAIL && password === ADMIN_PASSWORD) {
    sessionStorage.setItem('adminUser', email);
    window.location.href = 'home.html';
    return true;
  } else {
    alert('Invalid credentials');
    return false;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('loginForm');
  if (!form) {
    console.error('Login form not found');
    return;
  }

  form.addEventListener('submit', event => {
    event.preventDefault();
    const email = form.username.value;
    const password = form.password.value;
    loginAdmin(email, password);
  });
});
