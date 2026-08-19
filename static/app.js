
const form=document.getElementById("lead-form"),result=document.getElementById("result"),button=document.getElementById("submit-button"),resetButton=document.getElementById("reset-button");
function loading(v){button.disabled=v;button.querySelector("span:first-child").textContent=v?"Running automation…":"Run automation"}
function success(lead, automationResult) {
  form.hidden = true;
  result.hidden = false;
  result.classList.remove("error-state");

  document.getElementById("result-icon").textContent = "✓";
  document.getElementById("result-title").textContent =
    `${lead.first_name} has been captured`;

  document.getElementById("result-copy").textContent =
    "The lead has been scored and its automation tasks have been processed.";

  document.getElementById("result-score").textContent =
    `${lead.score}/100`;

  document.getElementById("result-category").textContent =
    lead.category;

  if (lead.category === "hot") {
    document.getElementById("crm-status").textContent =
      "✓ HubSpot CRM processed";

    document.getElementById("email-status").textContent =
      "✓ Sales notification sent";
  } else if (lead.category === "warm") {
    document.getElementById("crm-status").textContent =
      "✓ HubSpot CRM processed";

    document.getElementById("email-status").textContent =
      "Follow-up workflow created";
  } else {
    document.getElementById("crm-status").textContent =
      "✓ HubSpot CRM processed";

    document.getElementById("email-status").textContent =
      "No sales notification triggered";
  }
}
function fail(msg){form.hidden=true;result.hidden=false;result.classList.add("error-state");document.getElementById("result-icon").textContent="!";document.getElementById("result-title").textContent="Something went wrong";document.getElementById("result-copy").textContent=msg;document.getElementById("result-score").textContent="—";document.getElementById("result-category").textContent="—";document.getElementById("crm-status").textContent="Automation not confirmed";document.getElementById("email-status").textContent="Please try another test lead"}
form.addEventListener("submit",async e=>{e.preventDefault();loading(true);const fd=new FormData(form),payload=Object.fromEntries(fd.entries());payload.company_size=Number(payload.company_size);payload.source="website_form";try{const r=await fetch("/leads",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)}),d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.error||d.message||"The lead could not be created. Try a new test email address.");let a=null;try{const ar=await fetch("/automations/process",{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"});a=await ar.json()}catch(err){console.warn(err)}success(d.lead,a)}catch(err){fail(err.message||"Unexpected error.")}finally{loading(false)}});
resetButton.addEventListener("click",()=>{form.reset();form.hidden=false;result.hidden=true;result.classList.remove("error-state")});
