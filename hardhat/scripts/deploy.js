const hre = require("hardhat");

async function main() {
	
  const contractName = "Pujas"; 
  const contract = await hre.ethers.deployContract(contractName);

  await contract.waitForDeployment();

  console.log(`Contract Deployed to address ${await contract.getAddress()}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
