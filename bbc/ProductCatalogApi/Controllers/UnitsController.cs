using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using ProductCatalogApi.Data;
using ProductCatalogApi.Models;

namespace ProductCatalogApi.Controllers
{
    [ApiController]
    [Route("units")]
    public class UnitsController : ControllerBase
    {
        private readonly AppDbContext _context;

        public UnitsController(AppDbContext context)
        {
            _context = context;
        }

        [HttpGet]
        public async Task<IActionResult> GetAll()
        {
            var units = await _context.ProductUnits.ToListAsync();
            return Ok(units);
        }

        [HttpGet("{id}")]
        public async Task<IActionResult> GetById(int id)
        {
            var unit = await _context.ProductUnits.FindAsync(id);
            if (unit == null) return NotFound();
            return Ok(unit);
        }

        [HttpPost]
        public async Task<IActionResult> Post([FromBody] ProductUnit unit)
        {
            _context.ProductUnits.Add(unit);
            await _context.SaveChangesAsync();
            return CreatedAtAction(nameof(GetById), new { id = unit.ProductUnitId }, unit);
        }

        [HttpPut("{id}")]
        public async Task<IActionResult> Put(int id, [FromBody] ProductUnit unit)
        {
            if (id != unit.ProductUnitId) return BadRequest();
            _context.Entry(unit).State = EntityState.Modified;
            await _context.SaveChangesAsync();
            return NoContent();
        }

        [HttpDelete("{id}")]
        public async Task<IActionResult> Delete(int id)
        {
            var unit = await _context.ProductUnits.FindAsync(id);
            if (unit == null) return NotFound();
            _context.ProductUnits.Remove(unit);
            await _context.SaveChangesAsync();
            return NoContent();
        }
    }
}
