# GitHub Environment Preparation

This guide walks you through preparing your GitHub environment for MCPMark and authenticating the CLI tools with support for **token pooling** to mitigate rate limits.

## 📋 **Table of Contents**

<details>
<summary><strong>🔍 Quick Overview - Click to Expand</strong></summary>

### **Phase 1: GitHub Setup**
- [1.1 Create GitHub Organization](#1--prepare-your-evaluation-organization)
- [1.2 Create Multiple GitHub Accounts (Recommended)](#step-2-create-multiple-github-accounts-recommended)
- [1.3 Generate Personal Access Tokens (PATs)](#step-3-generate-fine-grained-personal-access-tokens-pats)
- [1.4 Configure Token Pooling](#step-4-configure-token-pooling-in-mcp_env)

### **Phase 2: Repository State Setup**
- [2.1 Download Sample Repositories](#2--download-the-sample-repository-state)
- [2.2 Extract and Verify Structure](#quick-setup)

### **Phase 3: Optional Customization**
- [3.1 Add Custom Repositories](#3--add-new-repositories-optional)
- [3.2 Update Configuration Files](#export-process)

### **Phase 4: Understanding Limits**
- [4.1 GitHub Rate Limits](#4--mitigating-github-rate-limits-with-token-pooling)
- [4.2 Token Pooling Benefits](#-token-pooling-benefits)

### **Phase 5: Verification & Troubleshooting**
- [5.1 Quick Checklist](#-quick-checklist)
- [5.2 Common Issues](#-troubleshooting)

**Total Estimated Time**: 20-30 minutes
**Difficulty Level**: ⭐⭐⭐☆☆ (Intermediate - requires multiple account setup)

</details>

---

## 🚨 Critical Requirements

> **⚠️ IMPORTANT**: You must enable **ALL permissions** for both Repository and Organization access. Partial permissions can cause authentication failures.

## 📋 **Table of Contents**

<details>
<summary><strong>🔍 Quick Overview - Click to Expand</strong></summary>

### **Phase 1: GitHub Setup**
- [1.1 Create GitHub Organization](#1--prepare-your-evaluation-organization)
- [1.2 Create Multiple GitHub Accounts (Recommended)](#step-2-create-multiple-github-accounts-recommended)
- [1.3 Generate Personal Access Tokens (PATs)](#step-3-generate-fine-grained-personal-access-tokens-pats)
- [1.4 Configure Token Pooling](#step-4-configure-token-pooling-in-mcp_env)

### **Phase 2: Repository State Setup**
- [2.1 Download Sample Repositories](#2--download-the-sample-repository-state)
- [2.2 Extract and Verify Structure](#quick-setup)

### **Phase 3: Optional Customization**
- [3.1 Add Custom Repositories](#3--add-new-repositories-optional)
- [3.2 Update Configuration Files](#export-process)

### **Phase 4: Understanding Limits**
- [4.1 GitHub Rate Limits](#4--mitigating-github-rate-limits-with-token-pooling)
- [4.2 Token Pooling Benefits](#-token-pooling-benefits)

### **Phase 5: Verification & Troubleshooting**
- [5.1 Quick Checklist](#-quick-checklist)
- [5.2 Common Issues](#-troubleshooting)

**Total Estimated Time**: 20-30 minutes
**Difficulty Level**: ⭐⭐⭐☆☆ (Intermediate - requires multiple account setup)

</details>

---

## 🚨 Critical Requirements

> **⚠️ IMPORTANT**: You must enable **ALL permissions** for both Repository and Organization access. Partial permissions can cause authentication failures.

## 1 · Prepare Your Evaluation Organization

---


## 2 · Download the Sample Repository State

We have pre-exported several popular open-source repositories along with curated Issues and PRs.
---

## 3 · Add New Repositories (Optional)

If you want to benchmark additional repositories:

### Export Process
1. **Export repository state**:
   ```bash
   python -m src.mcp_services.github.repo_exporter --repo owner/name --out ./github_state/{your_repo_name}
   ```
