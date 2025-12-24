# IVR Builder Installation Guide

## Overview
A complete IVR Flow Builder has been implemented for the Sip-Dialer project, including both frontend and backend components.

## What's Been Completed

### ✅ Frontend Components
1. **Visual Flow Builder** ([src/components/ivr/](Sip-Dialer/frontend/src/components/ivr/))
   - 9 custom node types with React Flow
   - Drag-and-drop canvas with minimap
   - Node configuration panels
   - Real-time flow editing

2. **Pages**
   - [IVRFlowsPage.tsx](Sip-Dialer/frontend/src/pages/IVRFlowsPage.tsx) - Flow list and management
   - [IVRBuilderPage.tsx](Sip-Dialer/frontend/src/pages/IVRBuilderPage.tsx) - Flow editor
   - [IVRBuilderPage_new.tsx](Sip-Dialer/frontend/src/pages/IVRBuilderPage_new.tsx) - Enhanced version with save/load

3. **Services**
   - [ivrService.ts](Sip-Dialer/frontend/src/services/ivrService.ts) - API client for IVR operations

4. **Type Definitions**
   - [types/ivr.ts](Sip-Dialer/frontend/src/types/ivr.ts) - Complete TypeScript definitions

### ✅ Backend API
1. **Models** (Already existed)
   - [app/models/ivr.py](Sip-Dialer/backend/app/models/ivr.py) - Database models

2. **Schemas**
   - [app/schemas/ivr.py](Sip-Dialer/backend/app/schemas/ivr.py) - Pydantic request/response schemas

3. **Service Layer**
   - [app/services/ivr_service.py](Sip-Dialer/backend/app/services/ivr_service.py) - Business logic

4. **API Endpoints**
   - [app/api/v1/endpoints/ivr.py](Sip-Dialer/backend/app/api/v1/endpoints/ivr.py) - REST API endpoints
   - Routes registered in [app/api/v1/router.py](Sip-Dialer/backend/app/api/v1/router.py)

### ✅ Configuration Updates
1. **App.tsx** - Updated to import IVRBuilderPage
2. **package.json** - Added reactflow dependency

## Installation Steps

### Step 1: Install Node.js
```bash
# Double-click the nodejs.msi file in C:\Users\Administrator\
# Follow the installation wizard
# Accept all defaults

# Verify installation
node --version
npm --version
```

### Step 2: Install Frontend Dependencies
```bash
cd C:\Users\Administrator\Sip-Dialer\frontend
npm install
```

This will install all dependencies including the newly added `reactflow` package.

### Step 3: Update App Routing (Manual)

The `IVRBuilderPage.tsx` has been created, but you need to update your App.tsx routing to include both the flow list and flow builder.

**Option A**: Use the simple version (current [IVRBuilderPage.tsx](Sip-Dialer/frontend/src/pages/IVRBuilderPage.tsx))
- This provides just the builder interface
- Good for testing

**Option B**: Use the full version with list (recommended)
1. Replace [IVRBuilderPage.tsx](Sip-Dialer/frontend/src/pages/IVRBuilderPage.tsx) with [IVRBuilderPage_new.tsx](Sip-Dialer/frontend/src/pages/IVRBuilderPage_new.tsx)
2. Add routing for both pages in [App.tsx](Sip-Dialer/frontend/src/App.tsx):

```typescript
import { IVRFlowsPage } from '@/pages/IVRFlowsPage';
import { IVRBuilderPage } from '@/pages/IVRBuilderPage';

// In your routes:
<Route path="ivr" element={<IVRFlowsPage />} />
<Route path="ivr/:flowId" element={<IVRBuilderPage />} />
```

### Step 4: Run Database Migrations

The IVR models already exist in the backend, but you may need to ensure the tables are created:

```bash
cd C:\Users\Administrator\Sip-Dialer\backend

# If using alembic
alembic upgrade head

# Or start the backend which will create tables automatically
python -m uvicorn app.main:app --reload
```

### Step 5: Start the Applications

**Backend:**
```bash
cd C:\Users\Administrator\Sip-Dialer\backend
python -m uvicorn app.main:app --reload
# Should start on http://localhost:8000
```

**Frontend:**
```bash
cd C:\Users\Administrator\Sip-Dialer\frontend
npm run dev
# Should start on http://localhost:3000
```

### Step 6: Access the IVR Builder

1. Login to your application
2. Navigate to the "IVR Builder" link in the sidebar
3. Click "New Flow" to create your first IVR flow
4. Use the visual builder to design your call flow

## API Endpoints

The following endpoints are now available:

### Flow Management
- `GET /api/v1/ivr/flows` - List all flows
- `POST /api/v1/ivr/flows` - Create new flow
- `GET /api/v1/ivr/flows/{id}` - Get flow details
- `PUT /api/v1/ivr/flows/{id}` - Update flow
- `DELETE /api/v1/ivr/flows/{id}` - Delete flow

### Version Management
- `POST /api/v1/ivr/flows/{id}/versions` - Save new version
- `GET /api/v1/ivr/flows/{id}/versions` - Get all versions
- `GET /api/v1/ivr/flows/{id}/versions/{version_id}` - Get specific version

## Features

### Node Types
1. **Start** - Entry point (always required)
2. **Play Audio** - Play audio files with optional DTMF wait
3. **Menu** - Present menu options with timeout/retries
4. **Survey Question** - Collect survey responses
5. **Record** - Record caller audio
6. **Transfer** - Transfer to another number
7. **Conditional** - Branch based on variables
8. **Set Variable** - Store call variables
9. **Hangup** - End the call

### Flow Operations
- **Visual Design** - Drag nodes, connect with edges
- **Configuration** - Click nodes to edit properties
- **Save/Load** - Persistent storage with versioning
- **Status Management** - Draft, Published, Archived states

## Troubleshooting

### Node.js Installation Issues
If the automatic installation doesn't work:
1. Download Node.js from https://nodejs.org/
2. Install version 18.x or higher (LTS recommended)
3. Restart your terminal after installation

### React Flow Import Errors
If you see "Cannot find module 'reactflow'":
```bash
cd C:\Users\Administrator\Sip-Dialer\frontend
npm install reactflow --save
```

### Backend Import Errors
If the backend fails to start with import errors:
```bash
cd C:\Users\Administrator\Sip-Dialer\backend
pip install -r requirements.txt
```

### CORS Issues
The backend should already have CORS configured for localhost:3000. If you see CORS errors:
1. Check that the backend is running on port 8000
2. Check that the frontend proxy in vite.config.ts points to http://localhost:8000

## Next Steps

### Immediate
1. ✅ Install Node.js
2. ✅ Run `npm install` in frontend directory
3. ✅ Choose routing strategy (Option A or B above)
4. ✅ Start both backend and frontend
5. ✅ Test creating a flow

### Future Enhancements
- Audio file picker integration
- Flow validation (check for disconnected nodes)
- Flow testing/simulation
- Flow templates
- Import/export flows
- Flowchart visualization in reports

## Documentation

- **Frontend README**: [IVR_BUILDER_README.md](Sip-Dialer/frontend/IVR_BUILDER_README.md)
- **Backend Models**: See [app/models/ivr.py](Sip-Dialer/backend/app/models/ivr.py) comments

## Support

For issues or questions:
1. Check the console for error messages
2. Verify all dependencies are installed
3. Ensure backend and frontend are both running
4. Check that database migrations have run
5. Review the browser network tab for API errors

## File Summary

### Created Files (20+)
**Frontend:**
- 9 node components
- 8 configuration components
- 1 main flow builder
- 1 node palette
- 1 config panel
- 3 page components
- 1 service file
- 1 types file

**Backend:**
- 1 schemas file
- 1 service file
- 1 endpoints file
- 1 router update

**Documentation:**
- 2 README files
- 1 installation guide

Total: 29 new files created!
