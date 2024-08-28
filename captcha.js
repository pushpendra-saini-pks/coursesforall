// captcha.js

function generateCaptcha() {
    const captcha = document.getElementById("captcha");
    const ctx = captcha.getContext("2d");
    const captchaText = Math.random().toString(36).substring(2, 8);
    ctx.clearRect(0, 0, captcha.width, captcha.height);
    ctx.font = "30px Arial";
    ctx.fillStyle = "#333";
    ctx.fillText(captchaText, 10, 30);

    // Store the captcha text in a hidden input field or in memory
    document.getElementById("captchaInput").dataset.captcha = captchaText;
}

function validateCaptcha() {
    const userCaptchaInput = document.getElementById("captchaInput").value;
    const generatedCaptcha = document.getElementById("captchaInput").dataset.captcha;

    if (userCaptchaInput === generatedCaptcha) {
        alert("CAPTCHA validated successfully!");
        return true;
    } else {
        alert("CAPTCHA validation failed. Please try again.");
        return false;
    }
}

document.getElementById("registerForm").onsubmit = validateCaptcha;
document.getElementById("loginForm").onsubmit = validateCaptcha;

window.onload = generateCaptcha;
