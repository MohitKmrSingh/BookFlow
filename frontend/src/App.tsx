import { useEffect, useState } from "react";
import type { ChangeEvent, FormEvent, ReactNode } from "react";
import { Link, Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { CalendarDays, Clock3, LogOut, Plus, Scissors, Users, CheckCircle2, ArrowRight, Sparkles } from "lucide-react";
import { getToken, json, request, setToken } from "./api";
import type { Appointment, Business, Hours, Me, Service, Slot, Staff } from "./types";

function Shell({children}:{children:ReactNode}) { return <div className="app-shell"><header className="topbar"><Link to="/" className="brand"><span className="brand-mark"><Scissors size={18}/></span>bookflow</Link><span className="top-note">Appointments, made simple</span></header>{children}<footer>© {new Date().getFullYear()} BookFlow · Simple scheduling for independent businesses</footer></div>; }
function Notice({error,success}:{error?:string;success?:string}) { return <>{error && <div className="notice error">{error}</div>}{success && <div className="notice success">{success}</div>}</>; }
function AuthPage() {
  const [mode,setMode]=useState<"login"|"register">("login"), [busy,setBusy]=useState(false), [error,setError]=useState("");
  const [form,setForm]=useState({business_name:"",full_name:"",email:"",password:"",phone:"",address:""});
  const nav=useNavigate();
  const change=(e:ChangeEvent<HTMLInputElement>)=>setForm({...form,[e.target.name]:e.target.value});
  async function submit(e:FormEvent) { e.preventDefault(); setBusy(true);setError("");try {
    if(mode==="register") { const r=await request<{access_token:string}>("/api/auth/register",json("POST",form));setToken(r.access_token); }
    else { const data=new URLSearchParams({username:form.email,password:form.password});const r=await request<{access_token:string}>("/api/auth/login",{method:"POST",headers:{"Content-Type":"application/x-www-form-urlencoded"},body:data});setToken(r.access_token); }
    nav("/dashboard");
  } catch(err){setError(err instanceof Error?err.message:"Something went wrong");}finally{setBusy(false);} }
  return <Shell><main className="auth-layout"><section className="auth-copy"><span className="eyebrow"><Sparkles size={14}/> BOOKFLOW FOR BUSINESS</span><h1>Your day,<br/><em>beautifully</em> booked.</h1><p>One calm place to manage your services, team and appointments. Give your customers a simpler way to book.</p><div className="feature-row"><span><CheckCircle2/> Easy online booking</span><span><CheckCircle2/> Your team in sync</span></div></section><section className="panel auth-panel"><div className="tabs"><button className={mode==="login"?"active":""} onClick={()=>setMode("login")}>Sign in</button><button className={mode==="register"?"active":""} onClick={()=>setMode("register")}>Create account</button></div><h2>{mode==="login"?"Welcome back":"Start your BookFlow"}</h2><p className="muted">{mode==="login"?"Sign in to manage your business.":"Set up your business workspace in minutes."}</p><Notice error={error}/><form onSubmit={submit} className="form-stack">
    {mode==="register" && <><label>Business name<input name="business_name" required minLength={2} value={form.business_name} onChange={change} placeholder="e.g. The Modern Studio"/></label><label>Your name<input name="full_name" required minLength={2} value={form.full_name} onChange={change} placeholder="Full name"/></label><label>Phone (optional)<input name="phone" value={form.phone} onChange={change} placeholder="+91..."/></label><label>Business address (optional)<input name="address" value={form.address} onChange={change} placeholder="City, area"/></label></>}
    <label>Email address<input name="email" type="email" required value={form.email} onChange={change} placeholder="you@example.com"/></label>
    <label>Password<input name="password" type="password" required minLength={8} value={form.password} onChange={change} placeholder="At least 8 characters"/></label>
    <button className="btn primary full" disabled={busy}>{busy?"Please wait…":mode==="login"?"Sign in":"Create my workspace"} <ArrowRight size={16}/></button>
  </form><p className="tiny muted">By continuing, you agree to use BookFlow responsibly. Keep your login details private.</p></section></main></Shell>;
}
function Protected({children}:{children:ReactNode}) { return getToken()?<>{children}</>:<Navigate to="/login" replace/>; }
function Dashboard() {
  const [me,setMe]=useState<Me|null>(null),[error,setError]=useState(""),[section,setSection]=useState("overview");
  const [services,setServices]=useState<Service[]>([]),[staff,setStaff]=useState<Staff[]>([]),[appointments,setAppointments]=useState<Appointment[]>([]);
  const [date,setDate]=useState(new Date(Date.now()-new Date().getTimezoneOffset()*60000).toISOString().slice(0,10));
  const [busy,setBusy]=useState(true),[toast,setToast]=useState("");
  const [rescheduling,setRescheduling]=useState<Appointment|null>(null);
  const [rescheduleDate,setRescheduleDate]=useState("");
  const [rescheduleStaffId,setRescheduleStaffId]=useState("");
  const [rescheduleSlots,setRescheduleSlots]=useState<Slot[]>([]);
  const [selectedRescheduleSlot,setSelectedRescheduleSlot]=useState("");
  const [savingReschedule,setSavingReschedule]=useState(false);
  const nav=useNavigate();
  async function load() {setBusy(true);setError("");try {const [m,s,t,a]=await Promise.all([request<Me>("/api/auth/me"),request<Service[]>("/api/services"),request<Staff[]>("/api/staff"),request<Appointment[]>(`/api/appointments?date=${date}`)]);setMe(m);setServices(s);setStaff(t);setAppointments(a);}catch(e){setError(e instanceof Error?e.message:"Unable to load dashboard");}finally{setBusy(false);}}
  useEffect(()=>{load();},[date]);

useEffect(()=>{
  if(!rescheduling || !rescheduleDate) return;

  let cancelled = false;
  setRescheduleSlots([]);
  setSelectedRescheduleSlot("");

  request<{slots:Slot[]}>(
    `/api/availability?service_id=${rescheduling.service_id}&date=${rescheduleDate}${rescheduleStaffId?`&staff_id=${rescheduleStaffId}`:""}`
  )
    .then(r=>{
      if(!cancelled) setRescheduleSlots(r.slots);
    })
    .catch(e=>{
      if(!cancelled){
        setRescheduleSlots([]);
        setError(e instanceof Error?e.message:"Could not load available slots");
      }
    });

  return ()=>{cancelled=true;};
},[rescheduling,rescheduleDate,rescheduleStaffId]);

  function logout(){setToken(null);nav("/login");}
  async function cancel(id:number){if(!confirm("Cancel this appointment?"))return;try{await request(`/api/appointments/${id}/cancel`,json("POST"));setToast("Appointment cancelled.");load();}catch(e){setError(e instanceof Error?e.message:"Could not cancel");}}
  async function status(id:number,value:string){try{await request(`/api/appointments/${id}/status`,json("PATCH",{status:value}));setToast("Appointment updated.");load();}catch(e){setError(e instanceof Error?e.message:"Could not update");}}
  
function startReschedule(a:Appointment){
  setError("");
  setRescheduleDate(a.appointment_date);
  setRescheduleStaffId(String(a.staff_id));
  setRescheduleSlots([]);
  setSelectedRescheduleSlot("");
  setRescheduling(a);
}
async function saveReschedule(){
  if(!rescheduling || !selectedRescheduleSlot) return;

  const slot = rescheduleSlots.find(
    s=>`${s.staff_id}-${s.start_time}`===selectedRescheduleSlot
  );

  if(!slot) return;

  setSavingReschedule(true);
  setError("");

  try{
    await request<Appointment>(
      `/api/appointments/${rescheduling.id}/reschedule`,
      json("POST",{
        appointment_date:rescheduleDate,
        start_time:slot.start_time,
        staff_id:slot.staff_id
      })
    );

    setToast("Appointment rescheduled successfully.");
    setRescheduling(null);
    setSelectedRescheduleSlot("");

    if(rescheduleDate===date){
      load();
    }else{
      setDate(rescheduleDate);
    }
  }catch(e){
    setError(e instanceof Error?e.message:"Could not reschedule appointment");
  }finally{
    setSavingReschedule(false);
  }
}

  const active=appointments.filter(a=>a.status==="confirmed"||a.status==="pending").length;
  return <Shell><div className="dashboard"><aside className="sidebar"><div className="business-mini"><div className="avatar">{me?.business.name?.slice(0,1)||"B"}</div><div><strong>{me?.business.name||"Your business"}</strong><small>Business workspace</small></div></div><nav>{[["overview","Overview",CalendarDays],["services","Services",Scissors],["staff","Team",Users]].map(([key,label,Icon]:any)=><button key={key} className={section===key?"selected":""} onClick={()=>setSection(key)}><Icon size={17}/>{label}</button>)}</nav><div className="sidebar-bottom"><button onClick={logout}><LogOut size={17}/> Sign out</button></div></aside>
  <main className="dash-main"><div className="dash-head"><div><span className="eyebrow">YOUR WORKSPACE</span><h1>{section==="overview"?"Good day.":section==="services"?"Your services":"Meet your team"}</h1><p className="muted">{section==="overview"?"Here’s what’s happening at your business.":section==="services"?"Manage what customers can book.":"Manage your staff and their working hours."}</p></div><div className="head-actions"><a className="btn secondary" href={`/book/${me?.business.slug||""}`} target="_blank" rel="noreferrer">Booking page <ArrowRight size={15}/></a><button className="icon-btn" title="Sign out" onClick={logout}><LogOut size={18}/></button></div></div>
  <Notice error={error} success={toast}/>{busy&&<p className="muted">Loading your workspace…</p>}
  {!busy&&section==="overview"&&<><div className="stats"><div className="stat-card"><span>Today's appointments</span><strong>{appointments.length}</strong><small>All statuses</small></div><div className="stat-card"><span>Upcoming / active</span><strong>{active}</strong><small>Pending or confirmed</small></div><div className="stat-card"><span>Active services</span><strong>{services.filter(s=>s.is_active).length}</strong><small>Available to customers</small></div><div className="stat-card"><span>Team members</span><strong>{staff.filter(s=>s.is_active).length}</strong><small>Active staff</small></div></div><section className="content-card"><div className="card-head"><div><h2>Appointments</h2><p className="muted">Bookings for the selected day</p></div><input aria-label="Appointment date" type="date" value={date} onChange={e=>setDate(e.target.value)}/></div>{appointments.length===0?<Empty title="No appointments yet" text="When customers book a slot, it will appear here."/>:<div className="table-wrap"><table><thead><tr><th>Time</th><th>Customer</th><th>Service</th><th>Team member</th><th>Status</th><th>Actions</th></tr></thead><tbody>{appointments.map(a=><tr key={a.id}><td className="time-cell">{a.start_time.slice(0,5)}–{a.end_time.slice(0,5)}</td><td><strong>{a.customer_name||"Customer"}</strong><small>#{a.id}</small></td><td>{a.service_name}</td><td>{a.staff_name}</td><td><span className={`status ${a.status}`}>{a.status.replace("_"," ")}</span></td><td><div className="row-actions">
  {a.status!=="cancelled"&&a.status!=="completed"&&<>
    <button onClick={()=>startReschedule(a)}>Reschedule</button>
    <button onClick={()=>status(a.id,"completed")}>Complete</button>
    <button className="danger-text" onClick={()=>cancel(a.id)}>Cancel</button>
  </>}
</div></td></tr>)}</tbody></table></div>}</section></>}
  {!busy&&section==="services"&&<ServicesPanel items={services} refresh={load}/>}
  {!busy&&section==="staff"&&<StaffPanel items={staff} refresh={load}/>}
  <section className="share-card"><div><span className="eyebrow">YOUR CUSTOMER BOOKING LINK</span><strong>{window.location.origin}/book/{me?.business.slug}</strong><small>Share this link so customers can book directly.</small></div><button className="btn secondary" onClick={()=>{navigator.clipboard.writeText(`${window.location.origin}/book/${me?.business.slug}`);setToast("Booking link copied.");}}>Copy link</button></section>
  {rescheduling&&<div className="modal-backdrop">
    <section className="content-card reschedule-modal">
      <div className="card-head">
        <div>
          <h2>Reschedule appointment #{rescheduling.id}</h2>
          <p className="muted">
            {rescheduling.customer_name} · {rescheduling.service_name}
          </p>
        </div>
        <button className="text-btn" onClick={()=>setRescheduling(null)}>
          Close
        </button>
      </div>

      <div className="form-stack">
        <label>
          New date
          <input
            type="date"
            min={new Date(Date.now()-new Date().getTimezoneOffset()*60000).toISOString().slice(0,10)}
            value={rescheduleDate}
            onChange={e=>setRescheduleDate(e.target.value)}
          />
        </label>

        <label>
          Team member
          <select
            value={rescheduleStaffId}
            onChange={e=>setRescheduleStaffId(e.target.value)}
          >
            {staff.filter(s=>s.is_active).map(s=>
              <option key={s.id} value={s.id}>{s.name}</option>
            )}
          </select>
        </label>

        <div>
          <strong>Available times</strong>
          {rescheduleSlots.length===0
            ? <p className="muted">No available slots for this date. Try another date or team member.</p>
            : <div className="slot-grid">
                {rescheduleSlots.map(slot=>
                  <button
                    type="button"
                    key={`${slot.staff_id}-${slot.start_time}`}
                    className={`slot ${selectedRescheduleSlot===`${slot.staff_id}-${slot.start_time}`?"chosen":""}`}
                    onClick={()=>setSelectedRescheduleSlot(`${slot.staff_id}-${slot.start_time}`)}
                  >
                    {slot.start_time.slice(0,5)}
                    <small>{slot.staff_name}</small>
                  </button>
                )}
              </div>
          }
        </div>

        <button
          className="btn primary full"
          disabled={!selectedRescheduleSlot||savingReschedule}
          onClick={saveReschedule}
        >
          {savingReschedule?"Saving…":"Save new appointment time"}
        </button>
      </div>
    </section>
  </div>}

  </main></div></Shell>;
}
function Empty({title,text}:{title:string;text:string}){return <div className="empty"><CalendarDays size={28}/><strong>{title}</strong><p>{text}</p></div>}
function ServicesPanel({items,refresh}:{items:Service[];refresh:()=>void}) {
 const [form,setForm]=useState({name:"",description:"",price:"",duration_minutes:"30"}),[error,setError]=useState(""),[busy,setBusy]=useState(false);
 async function add(e:FormEvent){e.preventDefault();setBusy(true);setError("");try{await request("/api/services",json("POST",{...form,price:Number(form.price),duration_minutes:Number(form.duration_minutes)}));setForm({name:"",description:"",price:"",duration_minutes:"30"});refresh();}catch(e){setError(e instanceof Error?e.message:"Could not add service");}finally{setBusy(false);}}
 async function toggle(s:Service){try{await request(`/api/services/${s.id}`,json("PATCH",{is_active:!s.is_active}));refresh();}catch(e){setError(e instanceof Error?e.message:"Update failed");}}
 return <div className="two-col"><section className="content-card"><div className="card-head"><div><h2>Service menu</h2><p className="muted">{items.length} services</p></div></div>{items.length===0?<Empty title="No services yet" text="Add your first service using the form."/>:<div className="item-list">{items.map(s=><div className="item-row" key={s.id}><div className="item-icon"><Scissors size={18}/></div><div className="item-main"><strong>{s.name}</strong><small>{s.duration_minutes} min · ₹{Number(s.price).toLocaleString("en-IN")}</small>{s.description&&<small>{s.description}</small>}</div><span className={`status ${s.is_active?"confirmed":"cancelled"}`}>{s.is_active?"Active":"Hidden"}</span><button className="text-btn" onClick={()=>toggle(s)}>{s.is_active?"Hide":"Activate"}</button></div>)}</div>}</section><section className="content-card"><h2>Add a service</h2><p className="muted">Set the price and how long it takes.</p><Notice error={error}/><form className="form-stack" onSubmit={add}><label>Service name<input required minLength={2} value={form.name} onChange={e=>setForm({...form,name:e.target.value})} placeholder="e.g. Haircut"/></label><label>Description<input value={form.description} onChange={e=>setForm({...form,description:e.target.value})} placeholder="Optional details"/></label><div className="field-grid"><label>Price (₹)<input required type="number" min="0" step="0.01" value={form.price} onChange={e=>setForm({...form,price:e.target.value})}/></label><label>Duration (minutes)<input required type="number" min="1" max="480" value={form.duration_minutes} onChange={e=>setForm({...form,duration_minutes:e.target.value})}/></label></div><button className="btn primary full" disabled={busy}><Plus size={16}/> Add service</button></form></section></div>;
}
const weekdays=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"];
function defaultHours():Omit<Hours,"id"|"staff_id">[]{return weekdays.map((_,weekday)=>({weekday,start_time:"09:00",end_time:"18:00",is_closed:weekday===6}));}
function StaffPanel({items,refresh}:{items:Staff[];refresh:()=>void}) {
 const [name,setName]=useState(""),[phone,setPhone]=useState(""),[email,setEmail]=useState(""),[hours,setHours]=useState(defaultHours()),[error,setError]=useState(""),[busy,setBusy]=useState(false);
 const [editing,setEditing]=useState<number|null>(null),[draft,setDraft]=useState<Hours[]>([]);
 function beginEdit(member:Staff){setEditing(member.id);setDraft(weekdays.map((_,weekday)=>{const saved=member.working_hours.find(h=>h.weekday===weekday);return saved?{...saved}:{weekday,start_time:"09:00",end_time:"18:00",is_closed:true};}));}
 async function saveHours(){if(editing===null)return;setError("");try{await request(`/api/staff/${editing}/working-hours`,json("PUT",draft.map(({weekday,start_time,end_time,is_closed})=>({weekday,start_time,end_time,is_closed}))));setEditing(null);refresh();}catch(e){setError(e instanceof Error?e.message:"Could not save working hours");}}
 async function add(e:FormEvent){e.preventDefault();setBusy(true);setError("");try{await request("/api/staff",json("POST",{name,phone:phone||null,email:email||null,working_hours:hours}));setName("");setPhone("");setEmail("");setHours(defaultHours());refresh();}catch(e){setError(e instanceof Error?e.message:"Could not add team member");}finally{setBusy(false);}}
 async function toggle(s:Staff){try{await request(`/api/staff/${s.id}`,json("PATCH",{is_active:!s.is_active}));refresh();}catch(e){setError(e instanceof Error?e.message:"Update failed");}}
 return <div className="two-col"><section className="content-card"><div className="card-head"><div><h2>Your team</h2><p className="muted">{items.length} team members</p></div></div>{items.length===0?<Empty title="Your team starts here" text="Add staff and set their weekly working hours."/>:<div className="item-list">{items.map(s=><div className="item-row" key={s.id}><div className="avatar small">{s.name.slice(0,1)}</div><div className="item-main"><strong>{s.name}</strong><small>{s.email||s.phone||"No contact details"}</small><small>{s.working_hours.filter(h=>!h.is_closed).length} working days per week</small></div><span className={`status ${s.is_active?"confirmed":"cancelled"}`}>{s.is_active?"Active":"Inactive"}</span><button className="text-btn" onClick={()=>beginEdit(s)}>Edit hours</button><button className="text-btn" onClick={()=>toggle(s)}>{s.is_active?"Deactivate":"Activate"}</button></div>)}</div>}
 {editing!==null&&<div className="hours-editor"><div className="card-head"><strong>Edit weekly hours</strong><button className="text-btn" onClick={()=>setEditing(null)}>Close</button></div>{draft.map((h,i)=><div className="hours-row" key={h.weekday}><label className="day-check"><input type="checkbox" checked={!h.is_closed} onChange={e=>setDraft(old=>old.map((v,j)=>j===i?{...v,is_closed:!e.target.checked}:v))}/>{weekdays[h.weekday].slice(0,3)}</label><input aria-label={`${weekdays[h.weekday]} start`} type="time" value={h.start_time} disabled={h.is_closed} onChange={e=>setDraft(old=>old.map((v,j)=>j===i?{...v,start_time:e.target.value}:v))}/><span>to</span><input aria-label={`${weekdays[h.weekday]} end`} type="time" value={h.end_time} disabled={h.is_closed} onChange={e=>setDraft(old=>old.map((v,j)=>j===i?{...v,end_time:e.target.value}:v))}/></div>)}<button className="btn primary full" onClick={saveHours}>Save working hours</button></div>}</section><section className="content-card"><h2>Add a team member</h2><p className="muted">Set weekly working hours for booking availability.</p><Notice error={error}/><form className="form-stack" onSubmit={add}><label>Full name<input required minLength={2} value={name} onChange={e=>setName(e.target.value)} placeholder="Team member name"/></label><div className="field-grid"><label>Phone<input value={phone} onChange={e=>setPhone(e.target.value)} placeholder="+91..."/></label><label>Email<input type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="Optional"/></label></div><div className="hours-list"><strong>Weekly hours</strong>{hours.map((h,i)=><div className="hours-row" key={h.weekday}><label className="day-check"><input type="checkbox" checked={!h.is_closed} onChange={e=>setHours(old=>old.map((v,j)=>j===i?{...v,is_closed:!e.target.checked}:v))}/>{weekdays[h.weekday].slice(0,3)}</label><input aria-label={`${weekdays[h.weekday]} start`} type="time" value={h.start_time} disabled={h.is_closed} onChange={e=>setHours(old=>old.map((v,j)=>j===i?{...v,start_time:e.target.value}:v))}/><span>to</span><input aria-label={`${weekdays[h.weekday]} end`} type="time" value={h.end_time} disabled={h.is_closed} onChange={e=>setHours(old=>old.map((v,j)=>j===i?{...v,end_time:e.target.value}:v))}/></div>)}</div><button className="btn primary full" disabled={busy}><Plus size={16}/> Add team member</button></form></section></div>;
}
function BookingPage() {
 const {slug=""}=useParams();const [business,setBusiness]=useState<Business|null>(null);const [services,setServices]=useState<Service[]>([]),[staff,setStaff]=useState<Staff[]>([]),[date,setDate]=useState(new Date(Date.now()+86400000-new Date().getTimezoneOffset()*60000).toISOString().slice(0,10)),[serviceId,setServiceId]=useState(""),[staffId,setStaffId]=useState(""),[slots,setSlots]=useState<Slot[]>([]),[selected,setSelected]=useState<Slot|null>(null),[customer,setCustomer]=useState({name:"",phone:"",email:""}),[error,setError]=useState(""),[success,setSuccess]=useState(""),[loading,setLoading]=useState(true),[submitting,setSubmitting]=useState(false);
 useEffect(()=>{Promise.all([request<Business>(`/api/public/${slug}`),request<Service[]>(`/api/public/${slug}/services`),request<Staff[]>(`/api/public/${slug}/staff`)]).then(([b,s,t])=>{setBusiness(b);setServices(s);setStaff(t);if(s[0])setServiceId(String(s[0].id));}).catch(e=>setError(e instanceof Error?e.message:"Could not load booking page")).finally(()=>setLoading(false));},[slug]);
 useEffect(()=>{if(!serviceId||!date)return;setSelected(null);request<{slots:Slot[]}>(`/api/public/${slug}/availability?service_id=${serviceId}&date=${date}${staffId?`&staff_id=${staffId}`:""}`).then(r=>setSlots(r.slots)).catch(e=>{setSlots([]);setError(e instanceof Error?e.message:"Could not load availability");});},[slug,serviceId,date,staffId]);
 async function book(e:FormEvent){e.preventDefault();if(!selected)return;setSubmitting(true);setError("");setSuccess("");try{const result=await request<Appointment>(`/api/public/${slug}/appointments`,json("POST",{service_id:Number(serviceId),staff_id:selected.staff_id,appointment_date:date,start_time:selected.start_time,customer:{...customer,email:customer.email.trim()||null}}));setSuccess(`Your booking is confirmed! Reference #${result.id}. ${result.appointment_date} at ${result.start_time.slice(0,5)} with ${result.staff_name}.`);setSelected(null);setCustomer({name:"",phone:"",email:""});const r=await request<{slots:Slot[]}>(`/api/public/${slug}/availability?service_id=${serviceId}&date=${date}${staffId?`&staff_id=${staffId}`:""}`);setSlots(r.slots);}catch(e){setError(e instanceof Error?e.message:"Booking failed");}finally{setSubmitting(false);}}
 const selectedService=services.find(s=>String(s.id)===serviceId);
 return <Shell><main className="booking-layout"><section className="booking-intro"><span className="eyebrow">BOOK YOUR VISIT</span><h1>A little time<br/><em>just for you.</em></h1><p>Choose a service, find a time that works and leave the rest to us.</p><div className="booking-benefit"><Clock3/> Easy online booking</div><div className="booking-benefit"><CheckCircle2/> Instant confirmation</div></section><section className="panel booking-panel"><div className="booking-heading"><span className="eyebrow">{business?.name||"BOOKFLOW APPOINTMENTS"}</span><h2>Reserve your appointment</h2><p className="muted">Complete the steps below to book your visit.</p></div><Notice error={error} success={success}/>{loading?<p>Loading services…</p>:services.length===0?<Empty title="Bookings unavailable" text="This business has not added any active services yet."/>:<form className="form-stack" onSubmit={book}><label>1. Choose a service<select required value={serviceId} onChange={e=>setServiceId(e.target.value)}>{services.map(s=><option value={s.id} key={s.id}>{s.name} · ₹{Number(s.price).toLocaleString("en-IN")} · {s.duration_minutes} min</option>)}</select></label><label>2. Choose a team member<select value={staffId} onChange={e=>setStaffId(e.target.value)}><option value="">Any available team member</option>{staff.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></label><label>3. Choose a date<input type="date" required min={new Date(Date.now()-new Date().getTimezoneOffset()*60000).toISOString().slice(0,10)} value={date} onChange={e=>setDate(e.target.value)}/></label><div><strong>4. Available times</strong>{slots.length===0?<p className="muted small-note">No slots found. Try another date or team member.</p>:<div className="slot-grid">{slots.map(slot=><button type="button" key={`${slot.staff_id}-${slot.start_time}`} className={`slot ${selected?.staff_id===slot.staff_id&&selected?.start_time===slot.start_time?"chosen":""}`} onClick={()=>setSelected(slot)}>{slot.start_time.slice(0,5)}<small>{slot.staff_name}</small></button>)}</div>}</div><div className="divider-line"/><strong>5. Your details</strong><div className="field-grid"><label>Your name<input required minLength={2} value={customer.name} onChange={e=>setCustomer({...customer,name:e.target.value})} placeholder="Full name"/></label><label>Phone number<input required minLength={8} value={customer.phone} onChange={e=>setCustomer({...customer,phone:e.target.value})} placeholder="+91..."/></label></div><label>Email (optional)<input type="email" value={customer.email} onChange={e=>setCustomer({...customer,email:e.target.value})} placeholder="you@example.com"/></label>{selected&&<div className="selected-slot"><CheckCircle2 size={17}/> {selectedService?.name} · {date} · {selected.start_time.slice(0,5)} with {selected.staff_name}</div>}<button className="btn primary full" disabled={!selected||submitting}>{submitting?"Confirming…":"Confirm appointment"} <ArrowRight size={16}/></button></form>}</section></main></Shell>;
}
export default function App(){return <Routes><Route path="/" element={<Navigate to={getToken()?"/dashboard":"/login"} replace/>}/><Route path="/login" element={getToken()?<Navigate to="/dashboard" replace/>:<AuthPage/>}/><Route path="/dashboard" element={<Protected><Dashboard/></Protected>}/><Route path="/book/:slug" element={<BookingPage/>}/><Route path="*" element={<Navigate to="/" replace/>}/></Routes>;}
