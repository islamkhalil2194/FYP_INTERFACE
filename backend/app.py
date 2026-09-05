from flask import Flask, jsonify, request
from flask_cors import CORS
from db import get_db_connection

app = Flask(__name__)
CORS(app)


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return jsonify({
        "system": "Smart Student Identity & Access Control System",
        "status": "online",
        "message": "Flask backend is running"
    })


# =========================================================
# TEST DATABASE CONNECTION
# =========================================================

@app.route("/api/test-db")
def test_database():

    connection = get_db_connection()

    if connection is None:
        return jsonify({
            "success": False,
            "message": "Could not connect to MySQL"
        }), 500

    try:

        cursor = connection.cursor()

        cursor.execute("SELECT DATABASE()")

        database = cursor.fetchone()[0]

        cursor.close()
        connection.close()

        return jsonify({
            "success": True,
            "database": database,
            "message": "MySQL connection successful"
        })

    except Exception as e:

        if connection:
            connection.close()

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# =========================================================
# SECURITY TERMINAL
# GET CARD INFORMATION USING RFID UID
# =========================================================

@app.route("/api/cards/<rfid_uid>", methods=["GET"])
def get_card_information(rfid_uid):

    connection = get_db_connection()

    if connection is None:
        return jsonify({
            "success": False,
            "message": "Database connection failed"
        }), 500

    try:

        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT
                s.student_id,
                s.reg_no,
                s.full_name,
                s.programme,
                s.year_of_study,
                s.enrollment_status,
                s.photo,

                r.card_id,
                r.rfid_uid,
                r.card_status,
                r.issue_date

            FROM rfid_cards r

            INNER JOIN students s
                ON r.student_id = s.student_id

            WHERE r.rfid_uid = %s

            LIMIT 1
        """

        cursor.execute(query, (rfid_uid,))

        record = cursor.fetchone()

        cursor.close()
        connection.close()

        # RFID NOT FOUND
        if record is None:

            return jsonify({
                "success": False,
                "found": False,
                "message": "RFID card not found"
            }), 404


        # Gate policy:
        # ACTIVE card = GRANTED
        # Anything else = DENIED

        access_granted = (
            record["card_status"] == "ACTIVE"
        )


        return jsonify({

            "success": True,

            "found": True,

            "student": {
                "student_id": record["student_id"],
                "reg_no": record["reg_no"],
                "full_name": record["full_name"],
                "programme": record["programme"],
                "year_of_study": record["year_of_study"],
                "enrollment_status": record["enrollment_status"],
                "photo": record["photo"]
            },

            "card": {
                "card_id": record["card_id"],
                "rfid_uid": record["rfid_uid"],
                "card_status": record["card_status"],
                "issue_date":
                    record["issue_date"].isoformat()
                    if record["issue_date"]
                    else None
            },

            "access": {
                "granted": access_granted,

                "decision":
                    "GRANTED"
                    if access_granted
                    else "DENIED",

                "reason":
                    "Active RFID card"
                    if access_granted
                    else "RFID card is inactive"
            }

        })

    except Exception as e:

        if connection:
            connection.close()

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# =========================================================
# ADMIN — LOOK UP CARD
#
# Search using:
#   RFID UID
#   Student ID
#   Registration Number
# =========================================================

@app.route("/api/admin/card-lookup", methods=["GET"])
def admin_card_lookup():

    search = request.args.get("search", "").strip()

    if not search:

        return jsonify({
            "success": False,
            "message": "Please provide a search value"
        }), 400


    connection = get_db_connection()

    if connection is None:

        return jsonify({
            "success": False,
            "message": "Database connection failed"
        }), 500


    try:

        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT

                s.student_id,
                s.reg_no,
                s.full_name,
                s.programme,
                s.year_of_study,
                s.enrollment_status,
                s.photo,

                r.card_id,
                r.rfid_uid,
                r.card_status,
                r.issue_date

            FROM rfid_cards r

            INNER JOIN students s
                ON r.student_id = s.student_id

            WHERE
                r.rfid_uid = %s
                OR s.reg_no = %s
                OR CAST(s.student_id AS CHAR) = %s

            LIMIT 1
        """

        cursor.execute(
            query,
            (search, search, search)
        )

        record = cursor.fetchone()

        cursor.close()
        connection.close()


        if record is None:

            return jsonify({
                "success": False,
                "found": False,
                "message": "No student or RFID card found"
            }), 404


        return jsonify({

            "success": True,
            "found": True,

            "student": {
                "student_id": record["student_id"],
                "reg_no": record["reg_no"],
                "full_name": record["full_name"],
                "programme": record["programme"],
                "year_of_study": record["year_of_study"],
                "enrollment_status": record["enrollment_status"],
                "photo": record["photo"]
            },

            "card": {
                "card_id": record["card_id"],
                "rfid_uid": record["rfid_uid"],
                "card_status": record["card_status"],
                "issue_date":
                    record["issue_date"].isoformat()
                    if record["issue_date"]
                    else None
            }

        })


    except Exception as e:

        if connection:
            connection.close()

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# =========================================================
# ADMIN — UPDATE CARD STATUS
#
# Allowed statuses:
#   ACTIVE
#   INACTIVE
# =========================================================

@app.route("/api/admin/cards/<int:card_id>/status", methods=["PUT"])
def update_card_status(card_id):

    data = request.get_json(silent=True) or {}

    new_status = str(
        data.get("card_status", "")
    ).strip().upper()


    if new_status not in ["ACTIVE", "INACTIVE"]:

        return jsonify({
            "success": False,
            "message": "Invalid card status. Use ACTIVE or INACTIVE."
        }), 400


    connection = get_db_connection()

    if connection is None:

        return jsonify({
            "success": False,
            "message": "Database connection failed"
        }), 500


    try:

        cursor = connection.cursor()


        # Check whether card exists

        cursor.execute(
            """
            SELECT card_id
            FROM rfid_cards
            WHERE card_id = %s
            """,
            (card_id,)
        )

        card = cursor.fetchone()


        if card is None:

            cursor.close()
            connection.close()

            return jsonify({
                "success": False,
                "message": "RFID card not found"
            }), 404


        # Update status

        cursor.execute(
            """
            UPDATE rfid_cards
            SET card_status = %s
            WHERE card_id = %s
            """,
            (new_status, card_id)
        )


        connection.commit()

        cursor.close()
        connection.close()


        return jsonify({

            "success": True,

            "message":
                f"Card status successfully changed to {new_status}",

            "card_id": card_id,

            "card_status": new_status

        })


    except Exception as e:

        if connection:
            connection.close()

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# =========================================================
# ADMIN — DASHBOARD STATISTICS
# =========================================================

@app.route("/api/admin/statistics", methods=["GET"])
def admin_statistics():

    connection = get_db_connection()

    if connection is None:

        return jsonify({
            "success": False,
            "message": "Database connection failed"
        }), 500


    try:

        cursor = connection.cursor(dictionary=True)


        # Total students

        cursor.execute(
            """
            SELECT COUNT(*) AS total_students
            FROM students
            """
        )

        total_students = cursor.fetchone()["total_students"]


        # Total RFID cards

        cursor.execute(
            """
            SELECT COUNT(*) AS total_cards
            FROM rfid_cards
            """
        )

        total_cards = cursor.fetchone()["total_cards"]


        # Active cards

        cursor.execute(
            """
            SELECT COUNT(*) AS active_cards
            FROM rfid_cards
            WHERE card_status = 'ACTIVE'
            """
        )

        active_cards = cursor.fetchone()["active_cards"]


        # Inactive cards

        cursor.execute(
            """
            SELECT COUNT(*) AS inactive_cards
            FROM rfid_cards
            WHERE card_status = 'INACTIVE'
            """
        )

        inactive_cards = cursor.fetchone()["inactive_cards"]


        cursor.close()
        connection.close()


        return jsonify({

            "success": True,

            "statistics": {

                "total_students": total_students,

                "total_cards": total_cards,

                "active_cards": active_cards,

                "inactive_cards": inactive_cards

            }

        })


    except Exception as e:

        if connection:
            connection.close()

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    print("---------------------------------------------")
    print("SMART STUDENT ACCESS CONTROL SYSTEM")
    print("Flask API starting...")
    print("---------------------------------------------")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )