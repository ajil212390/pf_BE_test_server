using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace ProductCatalogApi.Models
{
    [Table("productcategory")]
    public class ProductCategory
    {
        [Key]
        [Column("productcategoryid")]
        public int ProductCategoryId { get; set; }

        [Column("productcategoryname")]
        [MaxLength(100)]
        public string? ProductCategoryName { get; set; }
    }
}
