// A storage account, deliberately imperfect — the lab's linter and review steps
// find what's wrong with it. Compile with:  az bicep build --file main.bicep
//
// Bicep is a DSL that compiles to an ARM template. Nothing deploys it here; the
// whole lab runs offline, because `bicep build` and `bicep lint` never contact Azure.

@description('Azure region. Inherited from the resource group unless overridden.')
param location string = resourceGroup().location

@description('Globally unique storage account name — 3-24 chars, lowercase and digits only.')
@minLength(3)
@maxLength(24)
param storageName string

@description('Environment name, used for tagging and for the SKU decision below.')
@allowed(['dev', 'prod'])
param environment string = 'dev'

// ⭐ Unused, and the linter is about to say so. Left in on purpose — this is
// exactly how dead parameters survive in a real template nobody lints.
param retentionDays int = 7

var isProd = environment == 'prod'

resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageName
  location: location
  // In prod, replicate across zones. LRS keeps three copies in ONE datacentre,
  // so it survives a disk, not a building.
  sku: {
    name: isProd ? 'Standard_ZRS' : 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    // ⚠️ Both of these are wrong, and the DEFAULT linter says nothing about
    // either. Finding them is Break It scenario 2.
    supportsHttpsTrafficOnly: false
    minimumTlsVersion: 'TLS1_0'
    allowBlobPublicAccess: true
  }
  tags: {
    environment: environment
    managedBy: 'bicep'
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storage
  name: 'default'
}

resource uploads 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  parent: blobService
  name: 'uploads'
  properties: {
    publicAccess: 'None'
  }
}

output storageAccountName string = storage.name
output blobEndpoint string = storage.properties.primaryEndpoints.blob
