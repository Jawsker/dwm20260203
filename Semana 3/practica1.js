// const responseAPI = obtenerProductos(); // GET https://algo.cl/api/productos
const responseAPI = {
    "status": 200,
    "message": "Productos obtenidos correctamente",
    "data":[
        {
            "id": 1,
            "nombre": "Martillo",
            "precio": 3000
        },
        {
            "id": 2,
            "nombre": "Tijera",
            "precio": 1000
        }
    ]
};
responseAPI.data.forEach((producto) => {
    console.log(`Producto: ${producto.nombre} - $${producto.precio}`);
    console.log("<table>");
    console.log("<tr><td>NOMBRE</td><td>PRECIO</td></tr>");
    console.log(`<tr><td>${producto.nombre}</td><td>${producto.precio}</td></tr>`);
    console.log("</table>");
});
let variable1 = {"rut":"1-9"};
console.log(typeof(variable1));
let variable2;
console.log(typeof(variable2));
console.log(variable2 instanceof Object);
let variable3 = NaN;
console.log(typeof(variable3));
variable3 = 1/0;
console.log(typeof(variable3)); console.log(variable3);
variable3 = 1/variable1;
console.log(typeof(variable3)); console.log(variable3);

try{
    variable3 = variable3 + variable2;
}catch (err){
    console.log(`Error ${err}`);
}
