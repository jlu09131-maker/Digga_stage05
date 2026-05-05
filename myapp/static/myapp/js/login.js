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
    document.getElementById("togglePwd")?.addEventListener("click", () => {
        const pwd = document.getElementById("password");
        const icon = document.querySelector("#togglePwd .material-symbols-outlined");
        if (pwd.type === "password") {
            pwd.type = "text";
            if (icon) icon.textContent = "visibility_off";
        } else {
            pwd.type = "password";
            if (icon) icon.textContent = "visibility";
        }
    });

    const loginForm = document.getElementById("loginForm");
    if (!loginForm) { console.error("loginForm not found"); return; }

    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        const email    = document.getElementById("email")?.value?.trim();
        const password = document.getElementById("password")?.value;
        const btnText  = document.getElementById("btnText");
        const spinner  = document.getElementById("btnSpinner");
        const submitBtn = document.getElementById("submitBtn");

        if (!email || !password) {
            showToast("Please fill in all fields.", "warning");
            return;
        }

        if (btnText)  btnText.textContent = "Authenticating…";
        if (spinner)  spinner.classList.remove("hidden");
        if (submitBtn) submitBtn.disabled = true;

        try {
            const res = await fetch("/api/login/", {
                method:  "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken":  getCookie("csrftoken") || "",
                },
                body: JSON.stringify({ email, password }),
            });

            let data;
            try {
                data = await res.json();
            } catch {
                showToast("Server returned an invalid response. Check backend.", "error");
                return;
            }

            if (res.ok) {
                localStorage.setItem("access_token",  data.access);
                localStorage.setItem("refresh_token", data.refresh);
                localStorage.setItem("user_id",       data.user_id);
                localStorage.setItem("user_role",     data.role);
                localStorage.setItem("user_name",     data.name);
                localStorage.setItem("user_email",    data.email);

                showToast(`Welcome back, ${data.name}!`, "success");

                setTimeout(() => {
                    if (data.role === "Admin")       window.location.replace("/admin-dash/");
                    else if (data.role === "Driver") window.location.replace("/driver/");
                    else                             window.location.replace("/user/");
                }, 600);

            } else {
                const msg = data?.detail || data?.non_field_errors?.[0] || "Login failed. Check your credentials.";
                showToast(msg, "error");
            }

        } catch (err) {
            console.error("Login fetch error:", err);
            showToast("Cannot reach server. Is the backend running?", "error");
        } finally {
            if (btnText)   btnText.textContent = "AUTHENTICATE";
            if (spinner)   spinner.classList.add("hidden");
            if (submitBtn) submitBtn.disabled = false;
        }
    });
});