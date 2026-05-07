// HotelBench PMS - Application State and Logic

// Initial Data - 20 rooms, 15 occupied, realistic hotel data
const INITIAL_STATE = {
    rooms: [
        { number: '101', type: 'Standard King', status: 'occupied', guestName: 'Michael Chen', checkIn: '2025-01-10', checkOut: '2025-01-14', dnd: false, notes: [] },
        { number: '102', type: 'Standard King', status: 'occupied', guestName: 'Emily Rodriguez', checkIn: '2025-01-11', checkOut: '2025-01-14', dnd: false, notes: [] },
        { number: '103', type: 'Standard Queen', status: 'occupied', guestName: 'James Wilson', checkIn: '2025-01-12', checkOut: '2025-01-14', dnd: false, notes: [] },
        { number: '104', type: 'Standard Queen', status: 'vacant', guestName: '', checkIn: '', checkOut: '', dnd: false, notes: [] },
        { number: '105', type: 'Deluxe King', status: 'occupied', guestName: 'Sarah Johnson', checkIn: '2025-01-09', checkOut: '2025-01-14', dnd: false, notes: ['Prefers extra pillows'] },
        { number: '201', type: 'Standard King', status: 'occupied', guestName: 'Robert Brown', checkIn: '2025-01-11', checkOut: '2025-01-15', dnd: false, notes: [] },
        { number: '202', type: 'Standard King', status: 'dirty', guestName: '', checkIn: '', checkOut: '', dnd: false, notes: [] },
        { number: '203', type: 'Standard Queen', status: 'occupied', guestName: 'Lisa Anderson', checkIn: '2025-01-10', checkOut: '2025-01-14', dnd: true, notes: [] },
        { number: '204', type: 'Deluxe King', status: 'occupied', guestName: 'David Martinez', checkIn: '2025-01-08', checkOut: '2025-01-14', dnd: false, notes: [] },
        { number: '205', type: 'Suite', status: 'occupied', guestName: 'Jennifer Taylor', checkIn: '2025-01-11', checkOut: '2025-01-16', dnd: false, notes: ['VIP guest'] },
        { number: '220', type: 'Standard Queen', status: 'dirty', guestName: '', checkIn: '', checkOut: '', dnd: false, notes: [] },
        { number: '301', type: 'Standard King', status: 'occupied', guestName: 'William Thomas', checkIn: '2025-01-12', checkOut: '2025-01-15', dnd: false, notes: [] },
        { number: '302', type: 'Standard King', status: 'vacant', guestName: '', checkIn: '', checkOut: '', dnd: false, notes: [] },
        { number: '303', type: 'Deluxe King', status: 'occupied', guestName: 'Amanda White', checkIn: '2025-01-10', checkOut: '2025-01-14', dnd: false, notes: [] },
        { number: '312', type: 'Standard Queen', status: 'occupied', guestName: 'Christopher Lee', checkIn: '2025-01-11', checkOut: '2025-01-15', dnd: false, notes: [] },
        { number: '401', type: 'Standard King', status: 'occupied', guestName: 'Jessica Harris', checkIn: '2025-01-09', checkOut: '2025-01-14', dnd: false, notes: [] },
        { number: '402', type: 'Standard Queen', status: 'vacant', guestName: '', checkIn: '', checkOut: '', dnd: false, notes: [] },
        { number: '416', type: 'Deluxe King', status: 'occupied', guestName: 'Daniel Clark', checkIn: '2025-01-10', checkOut: '2025-01-15', dnd: false, notes: [] },
        { number: '501', type: 'Suite', status: 'occupied', guestName: 'Michelle Lewis', checkIn: '2025-01-11', checkOut: '2025-01-17', dnd: false, notes: ['Honeymoon package'] },
        { number: '502', type: 'Presidential Suite', status: 'maintenance', guestName: '', checkIn: '', checkOut: '', dnd: false, notes: ['Plumbing repair scheduled'] },
        { number: '108', type: 'Standard Queen', status: 'occupied', guestName: 'Kevin Walker', checkIn: '2025-01-12', checkOut: '2025-01-14', dnd: false, notes: [] }
    ],
    requests: [
        { id: 'REQ-001', room: '105', category: 'housekeeping', notes: 'Extra towels needed', priority: 'low', status: 'resolved', created: '2025-01-13 09:15' },
        { id: 'REQ-002', room: '203', category: 'maintenance', notes: 'TV remote not working', priority: 'medium', status: 'in-progress', created: '2025-01-13 10:30' },
        { id: 'REQ-003', room: '301', category: 'concierge', notes: 'Taxi booking for airport', priority: 'high', status: 'pending', created: '2025-01-13 11:00' },
        { id: 'REQ-004', room: '401', category: 'housekeeping', notes: 'Room service cleanup', priority: 'low', status: 'resolved', created: '2025-01-13 08:45' },
        { id: 'REQ-005', room: '501', category: 'concierge', notes: 'Champagne and strawberries', priority: 'high', status: 'resolved', created: '2025-01-13 14:00' },
        { id: 'REQ-006', room: '204', category: 'maintenance', notes: 'AC too cold', priority: 'medium', status: 'pending', created: '2025-01-13 15:30' },
        { id: 'REQ-007', room: '312', category: 'housekeeping', notes: 'Late checkout cleaning', priority: 'low', status: 'pending', created: '2025-01-13 16:00' },
        { id: 'REQ-008', room: '108', category: 'housekeeping', notes: 'More coffee pods', priority: 'low', status: 'pending', created: '2025-01-13 16:30' }
    ],
    nextRequestId: 9
};

// Current application state
let appState = JSON.parse(JSON.stringify(INITIAL_STATE));
let currentTab = 'dashboard';
let editingRoom = null;
let addingNoteRoom = null;

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    updateDateDisplay();
    setupTabNavigation();
    setupSearchFilters();
    renderAll();
});

function updateDateDisplay() {
    const now = new Date();
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    document.getElementById('current-date').textContent = now.toLocaleDateString('en-US', options);
}

function setupTabNavigation() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const tabId = e.target.dataset.tab;
            switchTab(tabId);
        });
    });
}

function switchTab(tabId) {
    currentTab = tabId;
    
    // Update tab buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabId);
    });
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === tabId);
    });
    
    // Re-render based on tab
    renderAll();
}

function setupSearchFilters() {
    // Room search
    const roomSearch = document.getElementById('room-search');
    if (roomSearch) {
        roomSearch.addEventListener('input', renderRoomsTable);
    }
    
    // Room filter
    const roomFilter = document.getElementById('room-filter');
    if (roomFilter) {
        roomFilter.addEventListener('change', renderRoomsTable);
    }
    
    // Request filter
    const requestFilter = document.getElementById('request-filter');
    if (requestFilter) {
        requestFilter.addEventListener('change', renderRequestsTable);
    }
    
    // Guest search
    const guestSearch = document.getElementById('guest-search');
    if (guestSearch) {
        guestSearch.addEventListener('input', renderGuestProfiles);
    }
}

function renderAll() {
    renderDashboard();
    renderRoomsTable();
    renderRequestsTable();
    renderGuestProfiles();
    populateRoomSelects();
}

function renderDashboard() {
    const occupied = appState.rooms.filter(r => r.status === 'occupied').length;
    const vacant = appState.rooms.filter(r => r.status === 'vacant').length;
    const dirty = appState.rooms.filter(r => r.status === 'dirty').length;
    const maintenance = appState.rooms.filter(r => r.status === 'maintenance').length;
    
    // Today's date for comparison
    const today = new Date().toISOString().split('T')[0];
    
    const arrivals = appState.rooms.filter(r => r.checkIn === today);
    const departures = appState.rooms.filter(r => r.checkOut === today && r.status === 'occupied');
    
    const occupancyRate = Math.round((occupied / appState.rooms.length) * 100);
    
    // Update stats
    document.querySelector('[data-testid="dashboard-total-rooms"]').textContent = appState.rooms.length;
    document.querySelector('[data-testid="dashboard-occupied"]').textContent = occupied;
    document.querySelector('[data-testid="dashboard-vacant"]').textContent = vacant + dirty + maintenance;
    document.querySelector('[data-testid="dashboard-dirty"]').textContent = dirty;
    document.querySelector('[data-testid="dashboard-arrivals"]').textContent = arrivals.length;
    document.querySelector('[data-testid="dashboard-departures"]').textContent = departures.length;
    document.querySelector('[data-testid="dashboard-occupancy-rate"]').textContent = occupancyRate + '%';
    
    // Render arrivals table
    const arrivalsBody = document.getElementById('dashboard-arrivals-body');
    arrivalsBody.innerHTML = arrivals.map(room => `
        <tr>
            <td data-testid="arrival-room-${room.number}">${room.number}</td>
            <td data-testid="arrival-guest-${room.number}">${room.guestName}</td>
            <td>3:00 PM</td>
            <td><span class="status-badge status-occupied">Expected</span></td>
        </tr>
    `).join('');
    
    // Render departures table
    const departuresBody = document.getElementById('dashboard-departures-body');
    departuresBody.innerHTML = departures.map(room => `
        <tr>
            <td data-testid="departure-room-${room.number}">${room.number}</td>
            <td data-testid="departure-guest-${room.number}">${room.guestName}</td>
            <td>11:00 AM</td>
            <td><span class="status-badge status-pending">Pending</span></td>
        </tr>
    `).join('');
}

function renderRoomsTable() {
    const tbody = document.getElementById('rooms-body');
    const searchTerm = document.getElementById('room-search')?.value.toLowerCase() || '';
    const filter = document.getElementById('room-filter')?.value || 'all';
    
    let filteredRooms = appState.rooms;
    
    if (searchTerm) {
        filteredRooms = filteredRooms.filter(r => r.number.includes(searchTerm));
    }
    
    if (filter !== 'all') {
        filteredRooms = filteredRooms.filter(r => r.status === filter);
    }
    
    tbody.innerHTML = filteredRooms.map(room => `
        <tr data-testid="room-row-${room.number}">
            <td data-testid="room-${room.number}-number">${room.number}</td>
            <td data-testid="room-${room.number}-type">${room.type}</td>
            <td>
                <span class="status-badge status-${room.status}" data-testid="room-${room.number}-status">
                    ${room.status}
                </span>
            </td>
            <td data-testid="room-${room.number}-guest">${room.guestName || '-'}</td>
            <td data-testid="room-${room.number}-checkin">${room.checkIn || '-'}</td>
            <td>
                <input type="time" 
                       value="${room.checkOut || '11:00'}" 
                       data-testid="room-${room.number}-checkout-input"
                       onchange="updateCheckoutTime('${room.number}', this.value)"
                       ${room.status !== 'occupied' ? 'disabled' : ''}>
            </td>
            <td>
                <input type="checkbox" 
                       class="dnd-checkbox"
                       data-testid="room-${room.number}-dnd"
                       ${room.dnd ? 'checked' : ''}
                       onchange="toggleDND('${room.number}')">
            </td>
            <td>
                <div class="room-actions">
                    <button class="btn btn-small btn-primary" 
                            data-testid="room-${room.number}-extend-checkout"
                            onclick="openCheckoutModal('${room.number}')">Extend</button>
                    ${room.status === 'dirty' ? `
                        <button class="btn btn-small btn-secondary" 
                                data-testid="room-${room.number}-mark-clean"
                                onclick="markRoomClean('${room.number}')">Mark Clean</button>
                    ` : ''}
                    ${room.status === 'vacant' ? `
                        <button class="btn btn-small btn-secondary" 
                                data-testid="room-${room.number}-mark-dirty"
                                onclick="markRoomDirty('${room.number}')">Mark Dirty</button>
                    ` : ''}
                </div>
            </td>
        </tr>
    `).join('');
}

function renderRequestsTable() {
    const tbody = document.getElementById('requests-body');
    const filter = document.getElementById('request-filter')?.value || 'all';
    
    let filteredRequests = appState.requests;
    
    if (filter !== 'all') {
        filteredRequests = filteredRequests.filter(r => r.status === filter);
    }
    
    tbody.innerHTML = filteredRequests.map(req => `
        <tr data-testid="request-row-${req.id}">
            <td data-testid="request-${req.id}-id">${req.id}</td>
            <td data-testid="request-${req.id}-room">${req.room}</td>
            <td data-testid="request-${req.id}-category">${req.category}</td>
            <td data-testid="request-${req.id}-notes">${req.notes}</td>
            <td>
                <span class="status-badge priority-${req.priority}" data-testid="request-${req.id}-priority">
                    ${req.priority}
                </span>
            </td>
            <td>
                <select data-testid="request-${req.id}-status-select"
                        onchange="updateRequestStatus('${req.id}', this.value)">
                    <option value="pending" ${req.status === 'pending' ? 'selected' : ''}>Pending</option>
                    <option value="in-progress" ${req.status === 'in-progress' ? 'selected' : ''}>In Progress</option>
                    <option value="resolved" ${req.status === 'resolved' ? 'selected' : ''}>Resolved</option>
                </select>
            </td>
            <td data-testid="request-${req.id}-created">${req.created}</td>
            <td>
                <button class="btn btn-small btn-secondary" 
                        data-testid="request-${req.id}-delete"
                        onclick="deleteRequest('${req.id}')">Delete</button>
            </td>
        </tr>
    `).join('');
}

function renderGuestProfiles() {
    const resultsDiv = document.getElementById('guest-results');
    const searchTerm = document.getElementById('guest-search')?.value.toLowerCase() || '';
    
    let filteredRooms = appState.rooms.filter(r => r.status === 'occupied');
    
    if (searchTerm) {
        filteredRooms = filteredRooms.filter(r => 
            r.number.includes(searchTerm) || 
            r.guestName.toLowerCase().includes(searchTerm)
        );
    }
    
    resultsDiv.innerHTML = filteredRooms.map(room => `
        <div class="guest-card" data-testid="guest-card-${room.number}">
            <div class="guest-card-header">
                <span class="guest-name" data-testid="guest-${room.number}-name">${room.guestName}</span>
                <span class="guest-room" data-testid="guest-${room.number}-room-label">Room ${room.number}</span>
            </div>
            <div class="guest-details">
                <div>
                    <div class="guest-detail-label">Check-in</div>
                    <div class="guest-detail-value" data-testid="guest-${room.number}-checkin">${room.checkIn}</div>
                </div>
                <div>
                    <div class="guest-detail-label">Check-out</div>
                    <div class="guest-detail-value" data-testid="guest-${room.number}-checkout">${room.checkOut}</div>
                </div>
                <div>
                    <div class="guest-detail-label">Room Type</div>
                    <div class="guest-detail-value" data-testid="guest-${room.number}-type">${room.type}</div>
                </div>
                <div>
                    <div class="guest-detail-label">DND Status</div>
                    <div class="guest-detail-value" data-testid="guest-${room.number}-dnd-status">${room.dnd ? 'Yes' : 'No'}</div>
                </div>
            </div>
            ${room.notes.length > 0 ? `
                <div class="guest-notes">
                    <div class="guest-notes-title">Notes:</div>
                    <ul data-testid="guest-${room.number}-notes">
                        ${room.notes.map(note => `<li>${note}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
            <div class="guest-actions">
                <button class="btn btn-small btn-primary" 
                        data-testid="guest-${room.number}-add-note"
                        onclick="openNoteModal('${room.number}')">Add Note</button>
                <button class="btn btn-small btn-secondary"
                        data-testid="guest-${room.number}-view-details"
                        onclick="alert('Full profile view coming soon')">View Details</button>
            </div>
        </div>
    `).join('');
}

function populateRoomSelects() {
    const selects = [
        document.getElementById('request-room'),
        document.getElementById('room-filter')
    ];
    
    // Only populate the request room select with room numbers
    const requestRoomSelect = document.getElementById('request-room');
    if (requestRoomSelect) {
        requestRoomSelect.innerHTML = appState.rooms.map(r => 
            `<option value="${r.number}">Room ${r.number} - ${r.guestName || 'Vacant'}</option>`
        ).join('');
    }
}

// Action Functions
function updateCheckoutTime(roomNumber, newTime) {
    const room = appState.rooms.find(r => r.number === roomNumber);
    if (room) {
        room.checkOut = newTime;
        renderAll();
    }
}

function toggleDND(roomNumber) {
    const room = appState.rooms.find(r => r.number === roomNumber);
    if (room) {
        room.dnd = !room.dnd;
        renderAll();
    }
}

function markRoomClean(roomNumber) {
    const room = appState.rooms.find(r => r.number === roomNumber);
    if (room) {
        room.status = 'vacant';
        renderAll();
    }
}

function markRoomDirty(roomNumber) {
    const room = appState.rooms.find(r => r.number === roomNumber);
    if (room) {
        room.status = 'dirty';
        renderAll();
    }
}

function openCheckoutModal(roomNumber) {
    editingRoom = roomNumber;
    const room = appState.rooms.find(r => r.number === roomNumber);
    document.getElementById('checkout-room-label').textContent = `Room ${roomNumber} - ${room.guestName}`;
    document.getElementById('checkout-time-input').value = room.checkOut || '11:00';
    document.getElementById('checkout-modal').classList.add('active');
}

function closeCheckoutModal() {
    document.getElementById('checkout-modal').classList.remove('active');
    editingRoom = null;
}

function saveCheckoutTime() {
    if (editingRoom) {
        const room = appState.rooms.find(r => r.number === editingRoom);
        const newTime = document.getElementById('checkout-time-input').value;
        if (room && newTime) {
            room.checkOut = newTime;
            renderAll();
            closeCheckoutModal();
        }
    }
}

function showNewRequestModal() {
    document.getElementById('request-modal').classList.add('active');
}

function closeRequestModal() {
    document.getElementById('request-modal').classList.remove('active');
    document.getElementById('new-request-form').reset();
}

function submitNewRequest(event) {
    event.preventDefault();
    
    const room = document.getElementById('request-room').value;
    const category = document.getElementById('request-category').value;
    const priority = document.getElementById('request-priority').value;
    const notes = document.getElementById('request-notes').value;
    
    const newRequest = {
        id: `REQ-${String(appState.nextRequestId).padStart(3, '0')}`,
        room,
        category,
        notes,
        priority,
        status: 'pending',
        created: new Date().toISOString().replace('T', ' ').substring(0, 16)
    };
    
    appState.requests.push(newRequest);
    appState.nextRequestId++;
    
    closeRequestModal();
    renderRequestsTable();
}

function updateRequestStatus(requestId, newStatus) {
    const request = appState.requests.find(r => r.id === requestId);
    if (request) {
        request.status = newStatus;
        renderRequestsTable();
    }
}

function deleteRequest(requestId) {
    appState.requests = appState.requests.filter(r => r.id !== requestId);
    renderRequestsTable();
}

function openNoteModal(roomNumber) {
    addingNoteRoom = roomNumber;
    const room = appState.rooms.find(r => r.number === roomNumber);
    document.getElementById('note-guest-label').textContent = `${room.guestName} - Room ${roomNumber}`;
    document.getElementById('note-input').value = '';
    document.getElementById('note-modal').classList.add('active');
}

function closeNoteModal() {
    document.getElementById('note-modal').classList.remove('active');
    addingNoteRoom = null;
}

function saveNote() {
    if (addingNoteRoom) {
        const room = appState.rooms.find(r => r.number === addingNoteRoom);
        const note = document.getElementById('note-input').value.trim();
        if (room && note) {
            room.notes.push(note);
            renderGuestProfiles();
            closeNoteModal();
        }
    }
}

// Utility function to reset state (for demo purposes)
function resetToInitialState() {
    appState = JSON.parse(JSON.stringify(INITIAL_STATE));
    renderAll();
}

// Expose functions globally for HTML onclick handlers
window.showNewRequestModal = showNewRequestModal;
window.closeRequestModal = closeRequestModal;
window.submitNewRequest = submitNewRequest;
window.openCheckoutModal = openCheckoutModal;
window.closeCheckoutModal = closeCheckoutModal;
window.saveCheckoutTime = saveCheckoutTime;
window.updateCheckoutTime = updateCheckoutTime;
window.toggleDND = toggleDND;
window.markRoomClean = markRoomClean;
window.markRoomDirty = markRoomDirty;
window.updateRequestStatus = updateRequestStatus;
window.deleteRequest = deleteRequest;
window.openNoteModal = openNoteModal;
window.closeNoteModal = closeNoteModal;
window.saveNote = saveNote;
window.resetToInitialState = resetToInitialState;
