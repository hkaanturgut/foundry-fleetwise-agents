using FleetWise.Api.Data;
using FleetWise.Api.Services;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers()
    .AddJsonOptions(o => o.JsonSerializerOptions.Converters.Add(new System.Text.Json.Serialization.JsonStringEnumConverter()));
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

builder.Services.AddDbContext<FleetWiseDbContext>(options =>
    options.UseSqlite(builder.Configuration.GetConnectionString("FleetWise") ?? "Data Source=fleetwise.db"));

builder.Services.AddSingleton<IClock, SystemClock>();
builder.Services.AddScoped<IVehicleService, VehicleService>();
builder.Services.AddScoped<IWorkOrderService, WorkOrderService>();
builder.Services.AddScoped<DispatcherService>();

var app = builder.Build();

using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<FleetWiseDbContext>();
    db.Database.EnsureCreated();
    SeedData.Seed(db, scope.ServiceProvider.GetRequiredService<IClock>());
}

app.UseSwagger();
app.UseSwaggerUI();

app.MapGet("/health", () => Results.Ok(new { status = "ok" }));
app.MapControllers();

app.Run();

public partial class Program
{
}
