import React, { useState } from "react";
import axios from "axios";
import "./App.css";
import Typewriter from "./Typewriter";
import logo from "./assets/logo.png";

const BASE_URL = "https://genomics-api-dev.calpoly.io/";

const App: React.FC = () => {
  const [authToken, setAuthToken] = useState<string>("");
  const [uploadGood, setUploadGood] = useState<boolean>(false);
  const [sraDownloadUrl, setSraDownloadUrl] = useState<string | null>(null);
  const [biosampleDownloadUrl, setBiosampleDownloadUrl] = useState<string | null>(null);
  const [sraMappingsJson, setSraMappingsJson] = useState<any>(null);
  const [biosampleMappingsJson, setBiosampleMappingsJson] = useState<any>(null);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);

  // Existing JSON input states
  const [jsonRulesInput, setJsonRulesInput] = useState<string>(
    JSON.stringify(
      {
        sra_manual_mappings: { "HAI WGS ID": "library_ID" },
        biosample_manual_mappings: { "HAI WGS ID": "strain" },
      },
      null,
      4
    )
  );

  const [jsonStaticRulesInput, setJsonStaticRulesInput] = useState<string>(
    JSON.stringify(
      {
        sra_static: { filename4: "asd.txt" },
        biosample_static: { bioproject_accession: "PRJNA288601" },
      },
      null,
      4
    )
  );

  // New JSON input states
  const [columnDefinitionsInput, setColumnDefinitionsInput] = useState<string>(
    JSON.stringify(
      {
        column_definitions: {"WSLH Specimen Number": "The ID used to track a specimen through the laboratory. Typically used internally."},
      },
      null,
      4
    )
  );

  const [staticRuleExclusionsInput, setStaticRuleExclusionsInput] = useState<string>(
    JSON.stringify(
      {
        sra_exclusions: {"Submitting State":"sample_name", "Genus":"library_ID"},
        biosample_exclusions: {"Date Collected":"sample_title", "Isolate Source":"bioproject_accession"},
      },
      null,
      4
    )
  );

  const [statusMessage, setStatusMessage] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setUploadedFile(e.target.files[0]);
    } else {
      setUploadedFile(null);
    }
  };

  const handleUploadAndProcess = async () => {
    if (!uploadedFile || !jsonRulesInput.trim()) {
      setStatusMessage("Please upload a file and provide valid JSON rules.");
      return;
    }

    let rulesDict: any;
    let staticRulesDict: any;
    let columnDefinitionsDict: any;
    let staticRuleExclusionsDict: any;

    try {
      rulesDict = JSON.parse(jsonRulesInput);
      if (jsonStaticRulesInput.trim()) {
        staticRulesDict = JSON.parse(jsonStaticRulesInput);
      }
      if (columnDefinitionsInput.trim()) {
        columnDefinitionsDict = JSON.parse(columnDefinitionsInput);
      }
      if (staticRuleExclusionsInput.trim()) {
        staticRuleExclusionsDict = JSON.parse(staticRuleExclusionsInput);
      }
    } catch (err) {
      setStatusMessage("Invalid JSON provided in one of the input fields.");
      return;
    }

    setIsLoading(true);
    setStatusMessage("Requesting presigned URL...");

    const params = new URLSearchParams();
    params.append("file_name", uploadedFile.name);
    params.append("upload", "True");
    params.append("json_rules", JSON.stringify(rulesDict));
    params.append("auth", authToken);

    if (staticRulesDict) {
      params.append("json_static_rules", JSON.stringify(staticRulesDict));
    }
    if (columnDefinitionsDict) {
      params.append("column_definitions", JSON.stringify(columnDefinitionsDict));
    }
    if (staticRuleExclusionsDict) {
      params.append("static_rule_exclusions", JSON.stringify(staticRuleExclusionsDict));
    }

    const requestUrl = `${BASE_URL}?${params.toString()}`;

    try {
      const response = await axios.get(requestUrl, { withCredentials: false });
      const { uuid, url } = response.data;

      setStatusMessage(url);
      await axios.put(url, uploadedFile, {
        headers: {
          "Content-Type": uploadedFile.type || "application/octet-stream",
        },
        withCredentials: false,
      });

      setStatusMessage("File uploaded successfully. Processing...");

      await new Promise((res) => setTimeout(res, 20000));

      const sraParams = new URLSearchParams({
        file_name: uploadedFile.name,
        upload: "False",
        uuid,
        sra: "True",
        auth: authToken,  // Add auth token to SRA download request
      });

      const sraResponse = await axios.get(`${BASE_URL}?${sraParams.toString()}`);
      if (sraResponse.status === 200) {
        setSraDownloadUrl(sraResponse.data.url);
        if (sraResponse.data.mappings) {
          setSraMappingsJson(sraResponse.data.mappings);
        }
      } else {
        setStatusMessage("Failed to fetch SRA download URL.");
      }

      const biosampleParams = new URLSearchParams({
        file_name: uploadedFile.name,
        upload: "False",
        uuid,
        sra: "False",
        auth: authToken,  // Add auth token to Biosample download request
      });

      const biosampleResponse = await axios.get(`${BASE_URL}?${biosampleParams.toString()}`);
      if (biosampleResponse.status === 200) {
        setBiosampleDownloadUrl(biosampleResponse.data.url);
        if (biosampleResponse.data.mappings) {
          setBiosampleMappingsJson(biosampleResponse.data.mappings);
        }
      } else {
        setStatusMessage("Failed to fetch Biosample download URL.");
      }

      setUploadGood(true);
      setStatusMessage("Processing complete! Download your files below.");
    } catch (error) {
      console.error("Error:", error);
      setStatusMessage("An unexpected error occurred.");
    } finally {
      setIsLoading(false);
    }
  };

  const downloadFile = async (url: string, filename: string) => {
    try {
      // Check if the URL already has parameters
      const hasParams = url.includes('?');
      const authParam = `auth=${authToken}`;
      
      // Append the auth token to the URL
      const urlWithAuth = hasParams 
        ? `${url}&${authParam}` 
        : `${url}?${authParam}`;
      
      const response = await axios.get(urlWithAuth, {
        responseType: "blob",
      });
      
      const blob = new Blob([response.data]);
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = filename;
      link.click();
    } catch (error) {
      console.error("Error downloading file:", error);
      setStatusMessage("Failed to download file.");
    }
  };

  let baseName = "";
  if (uploadedFile) {
    const nameParts = uploadedFile.name.split(".");
    baseName = nameParts.slice(0, -1).join(".");
  }

  return (
    <div className="app-container">
      <header className="header">
        <h1 className="text-4xl font-bold">
          <Typewriter words={["Welcome", "Genomics API Testing Interface"]} />
        </h1>
      </header>
      <div className="base-url">
        <p>API Base URL: <code>{BASE_URL}</code></p>
      </div>
      <main>
        <section className="file-upload-section">
          <label htmlFor="file-upload" className="file-label">
            Upload your file (CSV):
          </label>
          <input
            id="file-upload"
            type="file"
            accept=".csv"
            onChange={handleFileChange}
            className="file-input"
            aria-label="File Upload Input"
          />
        </section>
        <section className="auth-section">
          <label htmlFor="auth-token" className="auth-label">
            Authentication Token:
          </label>
          <input
            id="auth-token"
            type="text"
            value={authToken}
            onChange={(e) => setAuthToken(e.target.value)}
            className="auth-input"
            aria-label="Authentication Token Input"
          />
        </section>
        <section className="json-section">
          <h3>JSON Rules</h3>
          <textarea
            value={jsonRulesInput}
            onChange={(e) => setJsonRulesInput(e.target.value)}
            className="json-textarea"
            rows={15}
            cols={60}
            aria-label="JSON Rules Input"
          />
        </section>

        <section className="json-section">
          <h3>JSON Static Rules</h3>
          <textarea
            value={jsonStaticRulesInput}
            onChange={(e) => setJsonStaticRulesInput(e.target.value)}
            className="json-textarea"
            rows={15}
            cols={60}
            aria-label="JSON Static Rules Input"
          />
        </section>

        <section className="json-section">
          <h3>Column Definitions</h3>
          <textarea
            value={columnDefinitionsInput}
            onChange={(e) => setColumnDefinitionsInput(e.target.value)}
            className="json-textarea"
            rows={15}
            cols={60}
            aria-label="Column Definitions Input"
          />
        </section>

        <section className="json-section">
          <h3>Static Anti-Rules</h3>
          <textarea
            value={staticRuleExclusionsInput}
            onChange={(e) => setStaticRuleExclusionsInput(e.target.value)}
            className="json-textarea"
            rows={15}
            cols={60}
            aria-label="Static Anti-Rules Input"
          />
        </section>

        <button
          onClick={handleUploadAndProcess}
          disabled={isLoading}
          className="upload-button"
          aria-label="Upload and Process Button"
        >
          {isLoading ? "Processing..." : "Upload and Process"}
          {isLoading && <span className="spinner"></span>}
        </button>

        {statusMessage && <div className="status-message">{statusMessage}</div>}

        {uploadGood && (
          <section className="download-section">
            {sraDownloadUrl && (
              <button onClick={() => downloadFile(sraDownloadUrl, `${baseName}_sra.csv`)} className="download-button">
                Download SRA File
              </button>
            )}
            {biosampleDownloadUrl && (
              <button onClick={() => downloadFile(biosampleDownloadUrl, `${baseName}_biosample.csv`)} className="download-button">
                Download Biosample File
              </button>
            )}
          </section>
        )}

        {sraMappingsJson && (
          <section className="json-display-section">
            <h3>SRA Mappings JSON</h3>
            <pre className="json-output">{JSON.stringify(sraMappingsJson, null, 4)}</pre>
          </section>
        )}

        {biosampleMappingsJson && (
          <section className="json-display-section">
            <h3>Biosample Mappings JSON</h3>
            <pre className="json-output">{JSON.stringify(biosampleMappingsJson, null, 4)}</pre>
          </section>
        )}
      </main>

      <footer className="footer">
        <a href="https://dxhub.calpoly.edu/" target="_blank" rel="noopener noreferrer">
          <img src={logo} alt="Company Logo" className="footer-logo" />
        </a>
      </footer>
    </div>
  );
};

export default App;