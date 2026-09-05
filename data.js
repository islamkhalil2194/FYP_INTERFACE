/* =========================================================
   SMART STUDENT IDENTITY & ACCESS CONTROL SYSTEM
   DATA + FLASK API CONNECTION
   ========================================================= */

"use strict";


/* =========================================================
   1. FLASK API
   ========================================================= */

const API_BASE_URL = "http://localhost:5000/api";


/* =========================================================
   2. STAFF LOGIN DATABASE
   ========================================================= */

const STAFF_DB = {

    "STF-0231": {
        name: "James Mrema",
        initials: "JM",
        pin: "1234",
        levels: ["security"]
    },

    "STF-0099": {
        name: "Farida Kessy",
        initials: "FK",
        pin: "1234",
        levels: ["security", "admin"]
    }

};


/* =========================================================
   3. DEMO RFID CARDS
   =========================================================

   ACTIVE:
       A1B2C3D4

   This UID already exists in your MySQL database.

   IMPORTANT:
   INACTIVE-DEMO does NOT currently exist in your
   database. We will register an inactive card later.
   ========================================================= */

const DEMO_UIDS = {

    active: "A1B2C3D4",

    inactive: "INACTIVE-DEMO",

    unknown: "UNKNOWN-DEMO"

};


/* =========================================================
   4. ACCESS LEVEL INFORMATION
   ========================================================= */

const LEVEL_INFO = {

    security: {

        label: "Security Personnel",

        desc: "Verify student cards at assigned gates",

        color: "#E7A83B",

        bg: "rgba(231,168,59,0.13)",

        page: "terminal-security.html",

        icon: `
            <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.8"
            >
                <path
                    d="M12 2 4 5v6c0 5 3.4 8.9 8 11
                    4.6-2.1 8-6 8-11V5l-8-3Z"
                />
                <path d="m9 12 2 2 4-4" />
            </svg>
        `
    },


    admin: {

        label: "Main Staff / Admin",

        desc: "Manage students, cards, gates and logs",

        color: "#5D91D4",

        bg: "rgba(93,145,212,0.13)",

        page: "terminal-admin.html",

        icon: `
            <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.8"
            >
                <circle
                    cx="12"
                    cy="8"
                    r="3.5"
                />

                <path
                    d="M5 20c0-3.9 3.1-7 7-7s7 3.1 7 7"
                />
            </svg>
        `
    }

};


/* =========================================================
   5. URL PARAMETER HELPER
   ========================================================= */

function qs(name) {

    return new URLSearchParams(
        window.location.search
    ).get(name);

}


/* =========================================================
   6. REQUIRE STAFF LOGIN
   ========================================================= */

function requireStaff() {

    const id = qs("staff");

    const staff = STAFF_DB[id];

    if (!staff) {

        window.location.href = "index.html";

        return null;
    }

    return {

        id: id,

        ...staff

    };

}


/* =========================================================
   7. STAFF AUTHENTICATION
   ========================================================= */

function authenticateStaff(staffId, pin) {

    const staff = STAFF_DB[staffId];

    if (!staff) {

        return {

            success: false,

            message: "Staff ID not found."

        };

    }


    if (staff.pin !== pin) {

        return {

            success: false,

            message: "Incorrect PIN."

        };

    }


    return {

        success: true,

        staff: {

            id: staffId,

            ...staff

        }

    };

}


/* =========================================================
   8. GET CARD INFORMATION FROM FLASK
   ========================================================= */

async function getCardByUID(rfidUID) {

    if (!rfidUID || !rfidUID.trim()) {

        return {

            ok: false,

            status: 400,

            data: {

                success: false,

                found: false,

                message: "RFID UID is empty."

            }

        };

    }


    const cleanUID = rfidUID.trim();


    try {

        const response = await fetch(

            `${API_BASE_URL}/cards/${encodeURIComponent(cleanUID)}`,

            {
                method: "GET",

                headers: {
                    "Accept": "application/json"
                }
            }

        );


        let data;


        try {

            data = await response.json();

        } catch {

            data = {

                success: false,

                found: false,

                message: "Invalid response from Flask server."

            };

        }


        return {

            ok: response.ok,

            status: response.status,

            data: data

        };

    }


    catch (error) {

        console.error(
            "Flask connection error:",
            error
        );


        return {

            ok: false,

            status: 0,

            data: {

                success: false,

                found: false,

                message:
                    "Cannot connect to Flask. Make sure the backend is running on localhost:5000."

            }

        };

    }

}


/* =========================================================
   9. FORMAT API CARD RESULT
   ========================================================= */

function formatCardResult(apiResult) {

    if (!apiResult || !apiResult.data) {

        return {

            success: false,

            found: false,

            student: null,

            card: null,

            access: {

                granted: false,

                decision: "DENIED",

                reason: "No response received."

            },

            message: "No response received."

        };

    }


    const data = apiResult.data;


    /* -----------------------------------------------------
       CARD NOT FOUND
       ----------------------------------------------------- */

    if (!data.found) {

        return {

            success: false,

            found: false,

            student: null,

            card: null,

            access: {

                granted: false,

                decision: "DENIED",

                reason:
                    data.message ||
                    "RFID card not found."

            },

            message:
                data.message ||
                "RFID card not found."

        };

    }


    /* -----------------------------------------------------
       CARD FOUND
       ----------------------------------------------------- */

    return {

        success: true,

        found: true,

        student: data.student,

        card: data.card,

        access: data.access,

        message:
            data.access &&
            data.access.granted

                ? "Access granted."

                : "Access denied."

    };

}


/* =========================================================
   10. CHECK CARD STATUS
   ========================================================= */

function isCardActive(card) {

    if (!card) {

        return false;

    }

    return card.card_status === "ACTIVE";

}


/* =========================================================
   11. SIMULATE RFID SCAN
   ========================================================= */

async function simulateRFIDScan(type = "active") {

    const uid = DEMO_UIDS[type];


    if (!uid) {

        return {

            success: false,

            found: false,

            message: "No demonstration UID configured."

        };

    }


    console.log(
        "Simulating RFID scan:",
        uid
    );


    const apiResult =
        await getCardByUID(uid);


    return formatCardResult(apiResult);

}


/* =========================================================
   12. BACKEND CONNECTION CHECK
   ========================================================= */

async function checkBackendConnection() {

    try {

        const response =
            await fetch(
                `${API_BASE_URL}/test-db`
            );


        const data =
            await response.json();


        return {

            online:
                response.ok &&
                data.success === true,

            data: data

        };

    }


    catch (error) {

        return {

            online: false,

            data: {

                success: false,

                message:
                    "Flask backend is not reachable."

            }

        };

    }

}


/* =========================================================
   13. CURRENT TIME
   ========================================================= */

function timeNow() {

    return new Date()
        .toTimeString()
        .slice(0, 8);

}


/* =========================================================
   14. CURRENT DATE
   ========================================================= */

function dateNow() {

    return new Date()
        .toISOString()
        .slice(0, 10);

}


/* =========================================================
   15. FORMAT DATE
   ========================================================= */

function formatDate(dateString) {

    if (!dateString) {

        return "—";

    }


    const date =
        new Date(dateString);


    if (
        Number.isNaN(
            date.getTime()
        )
    ) {

        return dateString;

    }


    return date.toLocaleDateString(

        "en-GB",

        {
            day: "2-digit",

            month: "short",

            year: "numeric"
        }

    );

}


/* =========================================================
   16. CREATE INITIALS
   ========================================================= */

function getInitials(name) {

    if (!name) {

        return "?";

    }


    const words =
        name.trim().split(/\s+/);


    if (words.length === 1) {

        return words[0]
            .substring(0, 2)
            .toUpperCase();

    }


    return (

        words[0][0] +

        words[
            words.length - 1
        ][0]

    ).toUpperCase();

}


/* =========================================================
   17. TOAST MESSAGE
   ========================================================= */

function showToast(
    text,
    type = "info"
) {

    const toast =
        document.getElementById("toast");


    const toastText =
        document.getElementById("toastText");


    if (!toast || !toastText) {

        console.log(
            `[${type}]`,
            text
        );

        return;

    }


    toastText.textContent = text;


    toast.classList.remove(

        "success",

        "error",

        "warning",

        "info"

    );


    toast.classList.add(type);

    toast.classList.add("show");


    clearTimeout(
        window._toastTimer
    );


    window._toastTimer =
        setTimeout(

            () => {

                toast.classList.remove(
                    "show"
                );

            },

            2500

        );

}


/* =========================================================
   18. MAKE FUNCTIONS AVAILABLE TO HTML
   ========================================================= */

window.API_BASE_URL =
    API_BASE_URL;

window.STAFF_DB =
    STAFF_DB;

window.DEMO_UIDS =
    DEMO_UIDS;

window.LEVEL_INFO =
    LEVEL_INFO;

window.qs =
    qs;

window.requireStaff =
    requireStaff;

window.authenticateStaff =
    authenticateStaff;

window.getCardByUID =
    getCardByUID;

window.formatCardResult =
    formatCardResult;

window.isCardActive =
    isCardActive;

window.simulateRFIDScan =
    simulateRFIDScan;

window.checkBackendConnection =
    checkBackendConnection;

window.showToast =
    showToast;

window.timeNow =
    timeNow;

window.dateNow =
    dateNow;

window.formatDate =
    formatDate;

window.getInitials =
    getInitials;


console.log(
    "Smart Student Access System loaded."
);

console.log(
    "Flask API:",
    API_BASE_URL
);

console.log(
    "Active demo RFID:",
    DEMO_UIDS.active
);