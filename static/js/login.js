document.addEventListener("DOMContentLoaded", function () {
    // Flash message auto-hide
    const flashMessage = document.querySelector('.flash-message');
    if (flashMessage) {
        setTimeout(() => {
            flashMessage.style.display = 'none';
        }, 5000); // Hide after 5 seconds
    }

    // Password visibility toggle
    const passwordField = document.querySelector('#password');
    if (passwordField) {
        const showPasswordToggle = document.createElement('span');
        showPasswordToggle.innerHTML = '<i class="fa fa-eye"></i>';
        showPasswordToggle.style.cursor = 'pointer';
        showPasswordToggle.style.marginLeft = '10px';

        passwordField.parentNode.appendChild(showPasswordToggle);

        showPasswordToggle.addEventListener('click', function () {
            if (passwordField.type === 'password') {
                passwordField.type = 'text';
                showPasswordToggle.innerHTML = '<i class="fa fa-eye-slash"></i>';
            } else {
                passwordField.type = 'password';
                showPasswordToggle.innerHTML = '<i class="fa fa-eye"></i>';
            }
        });
    }

    // Countdown timer for verification page
    const timerElement = document.getElementById('timer');
    if (timerElement) {
        let countdown = 60;
        const countdownElement = timerElement.querySelector('.countdown');
        const timer = setInterval(function () {
            countdown--;
            countdownElement.textContent = countdown;

            if (countdown <= 10) {
                countdownElement.style.color = 'red'; // Change color to red when < 10 seconds
            }

            if (countdown <= 0) {
                clearInterval(timer);
                timerElement.innerHTML = 'Verification code has expired. Please log in again.';
                const submitButton = document.querySelector('button');
                if (submitButton) {
                    submitButton.disabled = true;
                }
            }
        }, 1000);
    }
});
