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
# DATABASE TEST
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
# RFID CARD LOOKUP
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

        if record is None:

            return jsonify({
                "success": False,
                "found": False,
                "message": "RFID card not found"
            }), 404

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
                "issue_date": (
                    record["issue_date"].isoformat()
                    if record["issue_date"]
                    else None
                )
            },

            "access": {
                "granted": access_granted,
                "decision": (
                    "GRANTED"
                    if access_granted
                    else "DENIED"
                ),
                "reason": (
                    "Active RFID card"
                    if access_granted
                    else "RFID card is inactive"
                )
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
# ADMIN SEARCH
# Search by:
# - RFID UID
# - Registration number
# - Student ID
# =========================================================

@app.route("/api/admin/search", methods=["GET"])
def admin_search():

    search = request.args.get("q", "").strip()

    if not search:

        return jsonify({
            "success": False,
            "message": "Search value is required"
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

            FROM students s

            LEFT JOIN rfid_cards r
                ON s.student_id = r.student_id

            WHERE
                s.reg_no = %s
                OR r.rfid_uid = %s
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
                "success": True,
                "found": False,
                "message": "No student or RFID card found"
            })

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
                "issue_date": (
                    record["issue_date"].isoformat()
                    if record["issue_date"]
                    else None
                )
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
# UPDATE RFID CARD STATUS
# Allowed:
# ACTIVE
# INACTIVE
# =========================================================

@app.route("/api/admin/cards/<int:card_id>/status", methods=["PUT"])
def update_card_status(card_id):

    data = request.get_json(silent=True)

    if not data:

        return jsonify({
            "success": False,
            "message": "Request body is required"
        }), 400

    new_status = str(
        data.get("status", "")
    ).strip().upper()

    if new_status not in ["ACTIVE", "INACTIVE"]:

        return jsonify({
            "success": False,
            "message": "Status must be ACTIVE or INACTIVE"
        }), 400

    connection = get_db_connection()

    if connection is None:

        return jsonify({
            "success": False,
            "message": "Database connection failed"
        }), 500

    try:

        cursor = connection.cursor()

        update_query = """
            UPDATE rfid_cards
            SET card_status = %s
            WHERE card_id = %s
        """

        cursor.execute(
            update_query,
            (new_status, card_id)
        )

        if cursor.rowcount == 0:

            cursor.close()
            connection.close()

            return jsonify({
                "success": False,
                "message": "RFID card not found"
            }), 404

        connection.commit()

        cursor.close()
        connection.close()

        return jsonify({
            "success": True,
            "message": f"Card status changed to {new_status}",
            "card_id": card_id,
            "card_status": new_status
        })

    except Exception as e:

        if connection:
            connection.rollback()
            connection.close()

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# =========================================================
# ADMIN STATISTICS
# =========================================================

@app.route("/api/admin/stats", methods=["GET"])
def admin_stats():

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
            "SELECT COUNT(*) AS total FROM students"
        )

        total_students = cursor.fetchone()["total"]

        # Total RFID cards
        cursor.execute(
            "SELECT COUNT(*) AS total FROM rfid_cards"
        )

        total_cards = cursor.fetchone()["total"]

        # Active cards
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM rfid_cards
            WHERE card_status = 'ACTIVE'
        """)

        active_cards = cursor.fetchone()["total"]

        # Inactive cards
        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM rfid_cards
            WHERE card_status = 'INACTIVE'
        """)

        inactive_cards = cursor.fetchone()["total"]

        cursor.close()
        connection.close()

        return jsonify({

            "success": True,

            "stats": {
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