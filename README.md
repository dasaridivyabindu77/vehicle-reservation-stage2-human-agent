# Vehicle Reservation Human-Agent

Run the application:

```bash
pip install -r requirements.txt
python app/main.py
```

Open `http://127.0.0.1:5000`. Complete a reservation flow in the chatbot, then use the **Administrator** button to approve or refuse pending requests.

Administrator REST endpoints:

- `GET /api/admin/requests`
- `POST /api/admin/respond` with `{"reference": "VR-...", "decision": "approve"}` or `{"decision": "refuse"}`
- `POST /api/admin/requests/<reference>/approve`
- `POST /api/admin/requests/<reference>/refuse`

After an administrator response, the user can send `status` in the chatbot to receive the latest confirmed or refused result.