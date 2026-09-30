using FleetWise.Api.Services;
using Microsoft.AspNetCore.Mvc;

namespace FleetWise.Api.Controllers;

[ApiController]
[Route("api/vehicles")]
public class VehiclesController : ControllerBase
{
    private readonly IVehicleService _vehicles;

    public VehiclesController(IVehicleService vehicles)
    {
        _vehicles = vehicles;
    }

    [HttpGet]
    public async Task<IActionResult> GetAll() => Ok(await _vehicles.GetAllAsync());

    [HttpGet("{id:int}")]
    public async Task<IActionResult> GetById(int id)
    {
        var vehicle = await _vehicles.GetByIdAsync(id);
        return vehicle is null ? NotFound() : Ok(vehicle);
    }

    public record UpdateOdometerRequest(int OdometerKm);

    [HttpPut("{id:int}/odometer")]
    public async Task<IActionResult> UpdateOdometer(int id, UpdateOdometerRequest request)
    {
        try
        {
            var vehicle = await _vehicles.UpdateOdometerAsync(id, request.OdometerKm);
            return vehicle is null ? NotFound() : Ok(vehicle);
        }
        catch (ArgumentException ex)
        {
            return BadRequest(new { error = ex.Message });
        }
    }
}
