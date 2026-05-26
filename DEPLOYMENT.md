# Deployment Guide: Render (Backend) & Vercel (Frontend)

To deploy this application to the internet and receive a live URL, we will host the Django REST API on **Render** (which provides a free PostgreSQL database) and the React frontend on **Vercel** (which is optimized for Vite/React apps).

---

## Part 1: Deploy the Backend to Render

1.  **Commit and Push:** Ensure all your latest code (including the newly added `render.yaml` and `build.sh`) is pushed to your GitHub `main` branch.
2.  **Sign up / Log in to Render**: Go to [Render.com](https://render.com) and log in with your GitHub account.
3.  **Create a New Blueprint Instance**:
    *   Click the **"New +"** button in the top right.
    *   Select **"Blueprint"** (this uses the `render.yaml` file to set everything up automatically).
    *   Connect your GitHub account and select the `breathe-esg-data-ingestion` repository.
    *   Click **Apply**.
4.  **Wait for the Build**:
    *   Render will automatically provision a free PostgreSQL database and a Web Service.
    *   It will run `./build.sh` (which installs requirements and runs migrations).
    *   *Note: The free tier of Render might take 3–5 minutes to spin up the first time.*
5.  **Get your Backend URL**:
    *   Once the "breathe-backend" service says **Live**, click on it.
    *   Copy the URL at the top left (it will look something like `https://breathe-backend-xxxx.onrender.com`). You need this for the frontend!

---

## Part 2: Deploy the Frontend to Vercel

1.  **Sign up / Log in to Vercel**: Go to [Vercel.com](https://vercel.com) and log in with your GitHub account.
2.  **Add New Project**:
    *   Click **"Add New..." -> "Project"**.
    *   Import your `breathe-esg-data-ingestion` repository from GitHub.
3.  **Configure the Project**:
    *   **Framework Preset**: Select `Vite` (it should auto-detect).
    *   **Root Directory**: Click "Edit" and type `frontend`. This is critical because the React code is inside the `frontend/` folder, not the root.
4.  **Environment Variables**:
    *   Expand the "Environment Variables" section.
    *   Add a new variable:
        *   **Name**: `VITE_API_BASE_URL`
        *   **Value**: `https://breathe-backend-xxxx.onrender.com/api/` *(Replace this with the exact URL you got from Render in Step 1. Make sure it ends with `/api/`)*
5.  **Deploy**:
    *   Click **Deploy**.
    *   Vercel will build the React app and give you a live URL within ~1 minute!

---

## Final Steps

*   **Test it**: Go to your live Vercel URL. Try uploading the `sample_data` CSVs. 
*   **Submit**: In your email back to the PM, include the **Vercel URL** as your live application link!
