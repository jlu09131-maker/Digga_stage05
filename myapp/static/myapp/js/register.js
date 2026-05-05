"use strict";

function getCookie(name) {
    if (!document.cookie) return null;
    for (const raw of document.cookie.split(";")) {
        const c = raw.trim();
        if (c.startsWith(name + "="))
            return decodeURIComponent(c.slice(name.length + 1));
    }
    return null;
}

document.addEventListener("DOMContentLoaded", function () {
    const registerForm = document.getElementById("registerForm");
    if (!registerForm) return;

    registerForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const name     = document.getElementById("name")?.value?.trim();
        const email    = document.getElementById("email")?.value?.trim();
        const mobile   = document.getElementById("mobile")?.value?.trim();
        const password = document.getElementById("password")?.value;
        const role     = document.getElementById("role")?.value;
        const submitBtn = registerForm.querySelector("button[type='submit']");

        if (!name || !email || !mobile || !password) {
            showToast("Please fill in all required fields.", "warning");
            return;
        }

        if (password.length < 8) {
            showToast("Password must be at least 8 characters.", "warning");
            return;
        }

        const origText = submitBtn?.textContent;
        if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = "Registering…"; }

        try {
            const res = await fetch("/api/persons/", {
                method:  "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken":  getCookie("csrftoken") || "",
                },
                body: JSON.stringify({ name, email, mobile, password, role }),
            });

            const data = await res.json();

            if (res.ok) {
                showToast("Account created! Redirecting to login…", "success");
                setTimeout(() => window.location.replace("/login-page/"), 1200);
            } else {
                let msg = "";
                if (data.detail) {
                    msg = data.detail;
                } else {
                    msg = Object.entries(data)
                        .map(([field, errs]) => `${field}: ${Array.isArray(errs) ? errs[0] : errs}`)
                        .join(" • ");
                }
                showToast(msg || "Registration failed.", "error");
            }

        } catch (err) {
            console.error("Register error:", err);
            showToast("Cannot reach server. Is the backend running?", "error");
        } finally {
            if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = origText; }
        }
    });
});