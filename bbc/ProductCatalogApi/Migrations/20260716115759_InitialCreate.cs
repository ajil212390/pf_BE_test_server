using System;
using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

namespace ProductCatalogApi.Migrations
{
    /// <inheritdoc />
    public partial class InitialCreate : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "company",
                columns: table => new
                {
                    companyid = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    companyname = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: true),
                    companyphonenumber = table.Column<long>(type: "bigint", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_company", x => x.companyid);
                });

            migrationBuilder.CreateTable(
                name: "productcategory",
                columns: table => new
                {
                    productcategoryid = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    productcategoryname = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_productcategory", x => x.productcategoryid);
                });

            migrationBuilder.CreateTable(
                name: "productunit",
                columns: table => new
                {
                    productunitid = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    productunitname = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_productunit", x => x.productunitid);
                });

            migrationBuilder.CreateTable(
                name: "users",
                columns: table => new
                {
                    userid = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    username = table.Column<string>(type: "character varying(120)", maxLength: 120, nullable: true),
                    useremail = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: true),
                    userpassword = table.Column<string>(type: "character varying(120)", maxLength: 120, nullable: true),
                    companyid = table.Column<int>(type: "integer", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_users", x => x.userid);
                    table.ForeignKey(
                        name: "FK_users_company_companyid",
                        column: x => x.companyid,
                        principalTable: "company",
                        principalColumn: "companyid");
                });

            migrationBuilder.CreateTable(
                name: "products",
                columns: table => new
                {
                    productid = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    productname = table.Column<string>(type: "character varying(150)", maxLength: 150, nullable: true),
                    productcategoryid = table.Column<int>(type: "integer", nullable: true),
                    productunitid = table.Column<int>(type: "integer", nullable: true),
                    productprice = table.Column<decimal>(type: "numeric", nullable: false),
                    productphotopath = table.Column<string>(type: "character varying(2000)", maxLength: 2000, nullable: true),
                    dateadded = table.Column<DateTime>(type: "timestamp with time zone", nullable: true),
                    userid = table.Column<int>(type: "integer", nullable: true),
                    companyid = table.Column<int>(type: "integer", nullable: true),
                    createdat = table.Column<DateTime>(type: "timestamp with time zone", nullable: true, defaultValueSql: "CURRENT_TIMESTAMP"),
                    addtype = table.Column<string>(type: "character varying(10)", maxLength: 10, nullable: true, defaultValue: "Single")
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_products", x => x.productid);
                    table.ForeignKey(
                        name: "FK_products_company_companyid",
                        column: x => x.companyid,
                        principalTable: "company",
                        principalColumn: "companyid");
                    table.ForeignKey(
                        name: "FK_products_productcategory_productcategoryid",
                        column: x => x.productcategoryid,
                        principalTable: "productcategory",
                        principalColumn: "productcategoryid");
                    table.ForeignKey(
                        name: "FK_products_productunit_productunitid",
                        column: x => x.productunitid,
                        principalTable: "productunit",
                        principalColumn: "productunitid");
                    table.ForeignKey(
                        name: "FK_products_users_userid",
                        column: x => x.userid,
                        principalTable: "users",
                        principalColumn: "userid");
                });

            migrationBuilder.CreateIndex(
                name: "IX_products_companyid",
                table: "products",
                column: "companyid");

            migrationBuilder.CreateIndex(
                name: "IX_products_productcategoryid",
                table: "products",
                column: "productcategoryid");

            migrationBuilder.CreateIndex(
                name: "IX_products_productunitid",
                table: "products",
                column: "productunitid");

            migrationBuilder.CreateIndex(
                name: "IX_products_userid",
                table: "products",
                column: "userid");

            migrationBuilder.CreateIndex(
                name: "IX_users_companyid",
                table: "users",
                column: "companyid");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "products");

            migrationBuilder.DropTable(
                name: "productcategory");

            migrationBuilder.DropTable(
                name: "productunit");

            migrationBuilder.DropTable(
                name: "users");

            migrationBuilder.DropTable(
                name: "company");
        }
    }
}
