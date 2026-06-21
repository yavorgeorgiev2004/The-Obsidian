/* ============================================
   THE OBSIDIAN — AUTH & DATA STORE
   localStorage-based session + hotel data
   ============================================ */

const OBS = {

  // ── SESSION ──────────────────────────────
  login(user) {
    localStorage.setItem('obs_user', JSON.stringify(user));
    localStorage.setItem('obs_login_time', Date.now());
  },
  logout() {
    localStorage.removeItem('obs_user');
    localStorage.removeItem('obs_login_time');
    window.location.href = 'login.html';
  },
  currentUser() {
    const u = localStorage.getItem('obs_user');
    return u ? JSON.parse(u) : null;
  },
  requireAuth(role) {
    const u = this.currentUser();
    if (!u) { window.location.href = 'login.html'; return null; }
    if (role && u.role !== role && u.role !== 'manager') {
      window.location.href = 'login.html'; return null;
    }
    return u;
  },
  requireGuest() {
    const u = this.currentUser();
    if (!u) { window.location.href = 'login.html'; return null; }
    return u;
  },

  // ── DEMO ACCOUNTS ────────────────────────
  accounts: [
    { id:'g1',  name:'James Holloway',    email:'guest@obsidian.com',      password:'guest123',   role:'guest',        points:1240 },
    { id:'g2',  name:'Sophia Chen',       email:'sophia@example.com',      password:'guest123',   role:'guest',        points:380  },
    { id:'r1',  name:'Elena Vasquez',     email:'reception@obsidian.com',  password:'staff123',   role:'receptionist', title:'Head Receptionist' },
    { id:'r2',  name:'Tom Whitfield',     email:'tom@obsidian.com',        password:'staff123',   role:'receptionist', title:'Receptionist'      },
    { id:'m1',  name:'Alexandra Reid',    email:'manager@obsidian.com',    password:'manager123', role:'manager',      title:'General Manager'   },
  ],

  authenticate(email, password) {
    return this.accounts.find(a => a.email === email && a.password === password) || null;
  },

  // ── ROOMS ────────────────────────────────
  initRooms() {
    if (localStorage.getItem('obs_rooms')) return;
    const rooms = [
      // Floor 2
      { id:'201', name:'Dark Room',          type:'dark-room',    floor:2, price:420,  status:'vacant',   clean:true,  notes:'' },
      { id:'202', name:'Dark Room',          type:'dark-room',    floor:2, price:420,  status:'occupied', clean:true,  notes:'DND until 2pm' },
      { id:'203', name:'Studio Suite',       type:'studio-suite', floor:2, price:580,  status:'booked',   clean:true,  notes:'Arriving 3pm' },
      { id:'204', name:'Dark Room',          type:'dark-room',    floor:2, price:420,  status:'vacant',   clean:false, notes:'' },
      { id:'205', name:'Studio Suite',       type:'studio-suite', floor:2, price:580,  status:'vacant',   clean:true,  notes:'' },
      { id:'206', name:'Dark Room',          type:'dark-room',    floor:2, price:420,  status:'maintenance', clean:false, notes:'Shower repair' },
      // Floor 3
      { id:'301', name:'Studio Suite',       type:'studio-suite', floor:3, price:580,  status:'occupied', clean:true,  notes:'' },
      { id:'302', name:'Dark Room',          type:'dark-room',    floor:3, price:420,  status:'vacant',   clean:true,  notes:'' },
      { id:'303', name:'Loft Suite',         type:'loft-suite',   floor:3, price:850,  status:'booked',   clean:true,  notes:'Anniversary — roses requested' },
      { id:'304', name:'Dark Room',          type:'dark-room',    floor:3, price:420,  status:'vacant',   clean:false, notes:'' },
      { id:'305', name:'Studio Suite',       type:'studio-suite', floor:3, price:580,  status:'occupied', clean:true,  notes:'Late checkout approved' },
      { id:'306', name:'Loft Suite',         type:'loft-suite',   floor:3, price:850,  status:'vacant',   clean:true,  notes:'' },
      // Floor 4
      { id:'401', name:'Loft Suite',         type:'loft-suite',   floor:4, price:850,  status:'vacant',   clean:true,  notes:'' },
      { id:'402', name:'Family Studio',      type:'family-studio', floor:4, price:580, status:'occupied', clean:true,  notes:'2 adults 2 children' },
      { id:'403', name:'Loft Suite',         type:'loft-suite',   floor:4, price:850,  status:'booked',   clean:true,  notes:'' },
      { id:'404', name:'Family Suite',       type:'family-suite', floor:4, price:1100, status:'vacant',   clean:true,  notes:'' },
      { id:'405', name:'Loft Suite',         type:'loft-suite',   floor:4, price:850,  status:'vacant',   clean:false, notes:'' },
      // Floor 5
      { id:'501', name:'Obsidian Suite',     type:'obsidian-suite', floor:5, price:1500, status:'occupied', clean:true, notes:'VIP — Mr. & Mrs. Yamamoto' },
      { id:'502', name:'Ultimate Family',    type:'family-ultimate', floor:5, price:1800, status:'vacant', clean:true, notes:'' },
      { id:'503', name:'Obsidian Suite',     type:'obsidian-suite', floor:5, price:1500, status:'booked', clean:true, notes:'Arriving tomorrow 6pm' },
      // Roof
      { id:'R01', name:'Void Penthouse',     type:'penthouse',    floor:6, price:4000, status:'vacant',   clean:true,  notes:'' },
    ];
    localStorage.setItem('obs_rooms', JSON.stringify(rooms));
  },

  getRooms() {
    this.initRooms();
    return JSON.parse(localStorage.getItem('obs_rooms'));
  },

  updateRoom(id, changes) {
    const rooms = this.getRooms();
    const idx = rooms.findIndex(r => r.id === id);
    if (idx === -1) return;
    rooms[idx] = { ...rooms[idx], ...changes };
    localStorage.setItem('obs_rooms', JSON.stringify(rooms));
  },

  // ── BOOKINGS ─────────────────────────────
  initBookings() {
    if (localStorage.getItem('obs_bookings')) return;
    const today = new Date();
    const fmt = d => d.toISOString().split('T')[0];
    const add = (d, n) => { const x=new Date(d); x.setDate(x.getDate()+n); return x; };

    const bookings = [
      {
        id:'BK001', guestId:'g1', guestName:'James Holloway',
        room:'202', roomName:'Dark Room', floor:2,
        checkIn: fmt(today), checkOut: fmt(add(today,3)),
        guests:2, status:'checked-in',
        packages:['welcome-champagne','breakfast-bed'],
        totalPrice:1260+45+65, depositPaid:true,
        specialRequests:'Quiet room please. Celebrating anniversary.',
        createdAt: fmt(add(today,-5))
      },
      {
        id:'BK002', guestId:'g2', guestName:'Sophia Chen',
        room:'203', roomName:'Studio Suite', floor:2,
        checkIn: fmt(today), checkOut: fmt(add(today,2)),
        guests:1, status:'due-in',
        packages:['spa-signature'],
        totalPrice:580*2+155, depositPaid:true,
        specialRequests:'Early check-in requested.',
        createdAt: fmt(add(today,-2))
      },
      {
        id:'BK003', guestId:'g1', guestName:'James Holloway',
        room:'303', roomName:'Loft Suite', floor:3,
        checkIn: fmt(add(today,7)), checkOut: fmt(add(today,10)),
        guests:2, status:'confirmed',
        packages:['anniversary-package'],
        totalPrice:850*3+225, depositPaid:true,
        specialRequests:'Roses in room please.',
        createdAt: fmt(add(today,-1))
      },
      {
        id:'BK004', guestId:'g2', guestName:'Sophia Chen',
        room:'301', roomName:'Studio Suite', floor:3,
        checkIn: fmt(add(today,-2)), checkOut: fmt(add(today,1)),
        guests:1, status:'checked-in',
        packages:['minibar'],
        totalPrice:580*3+95, depositPaid:true,
        specialRequests:'',
        createdAt: fmt(add(today,-10))
      },
      {
        id:'BK005', guestId:'g1', guestName:'James Holloway',
        room:'503', roomName:'Obsidian Suite', floor:5,
        checkIn: fmt(add(today,1)), checkOut: fmt(add(today,4)),
        guests:2, status:'confirmed',
        packages:['honeymoon-package','spa-day'],
        totalPrice:1500*3+195+295, depositPaid:true,
        specialRequests:'Surprise — please do not mention to guest.',
        createdAt: fmt(add(today,-3))
      },
    ];
    localStorage.setItem('obs_bookings', JSON.stringify(bookings));
  },

  getBookings() {
    this.initBookings();
    return JSON.parse(localStorage.getItem('obs_bookings'));
  },

  getBookingsForGuest(guestId) {
    return this.getBookings().filter(b => b.guestId === guestId);
  },

  addBooking(booking) {
    const bookings = this.getBookings();
    booking.id = 'BK' + String(Date.now()).slice(-6);
    booking.createdAt = new Date().toISOString().split('T')[0];
    bookings.push(booking);
    localStorage.setItem('obs_bookings', JSON.stringify(bookings));
    return booking;
  },

  updateBooking(id, changes) {
    const bookings = this.getBookings();
    const idx = bookings.findIndex(b => b.id === id);
    if (idx === -1) return;
    bookings[idx] = { ...bookings[idx], ...changes };
    localStorage.setItem('obs_bookings', JSON.stringify(bookings));
  },

  // ── PACKAGES ─────────────────────────────
  packages: [
    // Food & Drink
    { id:'welcome-champagne', category:'food',  name:'Welcome Champagne & Strawberries', price:45,  icon:'🥂', desc:'Moët & Chandon on arrival with fresh strawberries and chocolate.' },
    { id:'breakfast-bed',     category:'food',  name:'Breakfast in Bed for Two',         price:65,  icon:'🍳', desc:'Full Ember breakfast delivered to your room between 8am and 11am.' },
    { id:'ember-dinner',      category:'food',  name:'Ember Dinner Reservation',         price:185, icon:'🍽️', desc:'Table for two at Ember. Tasting menu included. Wine pairing optional.' },
    { id:'minibar',           category:'food',  name:'Minibar Stocked to Preference',    price:95,  icon:'🥃', desc:'Tell us your preferences and we will stock it before you arrive.' },
    { id:'celebration-cake',  category:'food',  name:'Celebration Cake',                 price:55,  icon:'🎂', desc:'Bespoke cake from the Ember kitchen. Flavour and message to your choice.' },
    // Spa
    { id:'spa-signature',     category:'spa',   name:'Obsidian Signature Massage',       price:155, icon:'💆', desc:'90 minute deep tissue with heated obsidian stones. Our signature treatment.' },
    { id:'spa-morning',       category:'spa',   name:'Morning Wellness — Pool & Yoga',   price:85,  icon:'🧘', desc:'Mineral pool, sauna, steam and rooftop yoga. Per person.' },
    { id:'spa-day',           category:'spa',   name:'Full Spa Day',                     price:295, icon:'✨', desc:'All treatments, pool, thermal suite and lunch in the Laurel Lounge.' },
    // Occasions
    { id:'honeymoon-package', category:'occasion', name:'Honeymoon Package',             price:195, icon:'💍', desc:'Flowers, champagne, rose petals, breakfast in bed. Everything.' },
    { id:'birthday-package',  category:'occasion', name:'Birthday Package',              price:145, icon:'🎁', desc:'Cake, balloons, surprise champagne and dinner reservation.' },
    { id:'anniversary-package',category:'occasion',name:'Anniversary Package',           price:225, icon:'💐', desc:'Flowers, champagne, candles and dinner for two at Ember.' },
    { id:'proposal-package',  category:'occasion', name:'Proposal Package',              price:495, icon:'💎', desc:'Location scouting, flowers, photographer, dinner reservation. The full story.' },
  ],

  getPackage(id) { return this.packages.find(p => p.id === id); },

  packageTotal(ids) {
    return ids.reduce((sum, id) => {
      const p = this.getPackage(id);
      return sum + (p ? p.price : 0);
    }, 0);
  },

  // ── CONCIERGE REQUESTS ───────────────────
  getRequests() {
    return JSON.parse(localStorage.getItem('obs_requests') || '[]');
  },
  addRequest(req) {
    const reqs = this.getRequests();
    req.id = 'RQ' + Date.now();
    req.status = 'pending';
    req.createdAt = new Date().toISOString();
    reqs.push(req);
    localStorage.setItem('obs_requests', JSON.stringify(reqs));
    return req;
  },
  updateRequest(id, changes) {
    const reqs = this.getRequests();
    const idx = reqs.findIndex(r => r.id === id);
    if (idx === -1) return;
    reqs[idx] = { ...reqs[idx], ...changes };
    localStorage.setItem('obs_requests', JSON.stringify(reqs));
  },

  // ── UTILITIES ────────────────────────────
  fmt: {
    date(str) {
      if (!str) return '—';
      return new Date(str).toLocaleDateString('en-GB', { day:'numeric', month:'short', year:'numeric' });
    },
    currency(n) { return '£' + Number(n).toLocaleString(); },
    statusBadge(status) {
      const map = {
        'vacant':      ['VACANT',      '#2a2a2a', '#888'],
        'occupied':    ['OCCUPIED',    '#1a2a1a', '#4caf50'],
        'booked':      ['BOOKED',      '#1a1a2a', '#8c7cff'],
        'maintenance': ['MAINTENANCE', '#2a1a1a', '#ff6b35'],
        'checked-in':  ['CHECKED IN',  '#1a2a1a', '#4caf50'],
        'due-in':      ['DUE IN',      '#1a1a2a', '#c9a84c'],
        'confirmed':   ['CONFIRMED',   '#1a2a2a', '#4cc9c9'],
        'checked-out': ['CHECKED OUT', '#2a2a2a', '#888'],
        'pending':     ['PENDING',     '#2a2a1a', '#c9a84c'],
        'complete':    ['COMPLETE',    '#1a2a1a', '#4caf50'],
        'cancelled':   ['CANCELLED',   '#2a1a1a', '#ff4444'],
      };
      const [label, bg, col] = map[status] || [status.toUpperCase(), '#222', '#aaa'];
      return `<span style="background:${bg};color:${col};font-size:0.55rem;letter-spacing:0.15em;padding:0.25rem 0.7rem;border:1px solid ${col}40;">${label}</span>`;
    },
    cleanBadge(clean) {
      return clean
        ? `<span style="background:#1a2a1a;color:#4caf50;font-size:0.52rem;letter-spacing:0.12em;padding:0.2rem 0.6rem;border:1px solid #4caf5040;">✓ CLEAN</span>`
        : `<span style="background:#2a1a1a;color:#ff9800;font-size:0.52rem;letter-spacing:0.12em;padding:0.2rem 0.6rem;border:1px solid #ff980040;">⚠ NEEDS CLEANING</span>`;
    },
    nights(checkIn, checkOut) {
      const a = new Date(checkIn), b = new Date(checkOut);
      return Math.round((b-a)/(1000*60*60*24));
    },
  },
};

// Auto-init data
OBS.initRooms();
OBS.initBookings();
