using FleetWise.Api.Services;
using Microsoft.AspNetCore.Mvc;

namespace FleetWise.Api.Controllers;

[ApiController]
[Route("api/workorders")]
public class WorkOrdersController : ControllerBase
{
    private readonly IWorkOrderService _workOrders;

    public WorkOrdersController(IWorkOrderService workOrders)
    {
        _workOrders = workOrders;
    }

    [HttpGet]
    public async Task<IActionResult> GetAll() => Ok(await _workOrders.GetAllAsync());

    [HttpGet("{id:int}")]
    public async Task<IActionResult> GetById(int id)
    {
        var workOrder = await _workOrders.GetByIdAsync(id);
        return workOrder is null ? NotFound() : Ok(workOrder);
    }

    [HttpPost]
    public async Task<IActionResult> Create(CreateWorkOrderRequest request)
    {
        var workOrder = await _workOrders.CreateAsync(request);
        return CreatedAtAction(nameof(GetById), new { id = workOrder.Id }, workOrder);
    }

    public record ScheduleRequest(DateTime ScheduledFor, int TechnicianId);

    [HttpPost("{id:int}/schedule")]
    public async Task<IActionResult> Schedule(int id, ScheduleRequest request)
    {
        try
        {
            var workOrder = await _workOrders.ScheduleAsync(id, request.ScheduledFor, request.TechnicianId);
            return workOrder is null ? NotFound() : Ok(workOrder);
        }
        catch (InvalidOperationException ex)
        {
            return Conflict(new { error = ex.Message });
        }
    }

    public record CompleteRequest(string TechnicianNotes);

    [HttpPost("{id:int}/complete")]
    public async Task<IActionResult> Complete(int id, CompleteRequest request)
    {
        try
        {
            var workOrder = await _workOrders.CompleteAsync(id, request.TechnicianNotes);
            return workOrder is null ? NotFound() : Ok(workOrder);
        }
        catch (InvalidOperationException ex)
        {
            return Conflict(new { error = ex.Message });
        }
    }
}
