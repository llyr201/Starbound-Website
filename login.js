const authApi = async (path, body) => {
	const response = await fetch(`/api/${path}`, {
		method: body ? 'POST' : 'GET',
		headers: body ? { 'Content-Type': 'application/json' } : {},
		credentials: 'same-origin',
		body: body ? JSON.stringify(body) : undefined
	});
	const result = await response.json();
	if (!response.ok) throw new Error(result.error || 'Something went wrong. Please try again.');
	return result;
};

const showStatus = (element, message, isError = false) => {
	if (!element) return;
	element.textContent = message;
	element.dataset.error = isError ? 'true' : 'false';
};

const setSubmitting = (form, submitting) => {
	const button = form.querySelector('button[type="submit"]');
	if (button) {
		button.disabled = submitting;
		button.textContent = submitting
			? 'Please wait...'
			: form.id === 'signupForm' ? 'Create account' : 'Sign in';
	}
};

const loginForm = document.querySelector('#loginForm');
const signupForm = document.querySelector('#signupForm');

if (loginForm) {
	loginForm.addEventListener('submit', async (event) => {
		event.preventDefault();
		const status = document.querySelector('#loginMessage');
		const values = new FormData(loginForm);
		showStatus(status, '');
		setSubmitting(loginForm, true);
		try {
			await authApi('login', {
				username: values.get('username'),
				password: values.get('password')
			});
			window.location.assign('/home.html');
		} catch (error) {
			showStatus(status, error.message, true);
			setSubmitting(loginForm, false);
		}
	});
}

if (signupForm) {
	signupForm.addEventListener('submit', async (event) => {
		event.preventDefault();
		const status = document.querySelector('#signupMessage');
		const values = new FormData(signupForm);
		if (values.get('password') !== values.get('confirmPassword')) {
			showStatus(status, 'Passwords do not match.', true);
			return;
		}
		showStatus(status, '');
		setSubmitting(signupForm, true);
		try {
			await authApi('signup', {
				username: values.get('username'),
				email: values.get('email'),
				password: values.get('password')
			});
			window.location.assign('/home.html');
		} catch (error) {
			showStatus(status, error.message, true);
			setSubmitting(signupForm, false);
		}
	});
}

document.querySelectorAll('.sign-out').forEach((button) => {
	button.addEventListener('click', async () => {
		button.disabled = true;
		try {
			await authApi('logout', {});
		} finally {
			window.location.assign('/');
		}
	});
});

if (!loginForm && !signupForm) {
	authApi('me').then(({ user }) => {
		if (!user) {
			window.location.replace('/');
			return;
		}
		const avatar = document.querySelector('.account .avatar');
		if (avatar) avatar.textContent = user.username.slice(0, 2).toUpperCase();
	}).catch(() => window.location.replace('/'));
}
