// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract Pujas {
    struct Puja {
        address arrendatario;
        uint monto;
        string moneda;
    }
    
    Puja[] public pujas;

    function registrarPuja(address _arrendatario, uint _monto, string memory _moneda) public {
        Puja memory nuevaPuja = Puja({
            arrendatario: _arrendatario,
            monto: _monto,
            moneda: _moneda
        });
        pujas.push(nuevaPuja);
    }

    function obtenerPuja(uint index) public view returns (address, uint, string memory) {
        Puja memory p = pujas[index];
        return (p.arrendatario, p.monto, p.moneda);
    }

    function numeroDePujas() public view returns (uint) {
        return pujas.length;
    }
}
