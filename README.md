# 🛣️ Fuel Route Optimizer

An intelligent, cost-efficient **fuel stop planner API** built with Django, Django Ninja (async), Celery, Redis, PostGIS, and Geoapify.  
It calculates the **cheapest fuel stops** along a route in the USA, given a vehicle's limited fuel range (e.g., 500 miles).

---

## 🌐 Live Demo

🔗 **API Docs**: [https://fuel-route-optimizer.onrender.com/docs](https://fuel-route-optimizer.onrender.com/docs)

Test endpoints, review schemas, and try the route planner with real input.

---

## 🧱 Tech Stack

- **Backend**: Django, Django Ninja (Async APIs)
- **Geospatial**: GeoDjango, PostGIS, Geoapify API
- **Database**: PostgreSQL + PostGIS
- **Task Queue**: Celery with Redis broker + result backend
- **Caching**: Redis (with custom locks and key strategies)
- **Asynchronous Processing**: Celery Background Tasks
- **Deployment-ready**: Dockerized + `.env` support

---

## 🚀 Features

- 🔁 Async APIs using `@api_controller`, `http_get`, `http_post`
- 🗺️ Route segmentation, spatial filtering, and map-based calculations
- ⛽ Fuel station data loader (CSV) using `PointField` (GeoDjango)
- 💰 Calculates total fuel cost based on fuel price & MPG
- 🧠 Intelligent 500-mile chunk segmentation and optimal station selection
- 🔐 Secure, scalable, production-ready architecture

---

## ⚙️ Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/your-username/fuel-route-optimizer.git
cd fuel-route-optimizer

# 2. Create and activate virtual environment
python -m venv env
source env/bin/activate    
env\Scripts\activate #for Windows
# 3. Install Python requirements
pip install -r requirements.txt

# 4. Create .env file from example
cp .env.example .env

# 5. Run migrations
python manage.py migrate

# 6. Load fuel station CSV (if available)
python manage.py load_fuel_stations fuel_stations.csv

# 7. Run development server
python manage.py runserver
