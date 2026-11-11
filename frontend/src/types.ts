export type User = { id:number; business_id:number; email:string; full_name:string; role:string; is_active:boolean };
export type Business = { id:number; name:string; slug:string; address:string|null; phone:string|null; timezone:string };
export type Me = { user:User; business:Business };
export type Service = { id:number; business_id:number; name:string; description:string|null; price:string|number; duration_minutes:number; is_active:boolean };
export type Hours = { id?:number; staff_id?:number; weekday:number; start_time:string; end_time:string; is_closed:boolean };
export type Staff = { id:number; business_id:number; name:string; phone:string|null; email:string|null; is_active:boolean; working_hours:Hours[] };
export type Appointment = { id:number; business_id:number; customer_id:number; service_id:number; staff_id:number; appointment_date:string; start_time:string; end_time:string; status:string; notes:string|null; customer_name:string|null; service_name:string|null; staff_name:string|null };
export type Slot = { start_time:string; end_time:string; staff_id:number; staff_name:string };
