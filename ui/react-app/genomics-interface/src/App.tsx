// src/App.tsx 
import React, { useState } from "react";
import axios from "axios";
import "./App.css";
import Typewriter from "./Typewriter";
import logo from "./assets/logo.png";

const BASE_URL = "https://r9yk6nnowk.execute-api.us-west-2.amazonaws.com/";

const App: React.FC = () => {
  const [uploadGood, setUploadGood] = useState<boolean>(false);
  const [sraDownloadUrl, setSraDownloadUrl] = useState<string | null>(null);
  const [biosampleDownloadUrl, setBiosampleDownloadUrl] = useState<string | null>(null);
  
  // **Change 1:** Add separate state for SRA and Biosample mappings
  const [sraMappingsJson, setSraMappingsJson] = useState<any>(null); // New state for SRA mappings JSON
  const [biosampleMappingsJson, setBiosampleMappingsJson] = useState<any>(null); // New state for Biosample mappings JSON

  const [uploadedFile, setUploadedFile] = useState<File | null>(null);

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
    try {
      rulesDict = JSON.parse(jsonRulesInput);
    } catch (err) {
      setStatusMessage("Invalid JSON provided in the rules text area.");
      return;
    }

    let staticRulesDict: any;
    if (jsonStaticRulesInput.trim()) {
      try {
        staticRulesDict = JSON.parse(jsonStaticRulesInput);
      } catch (err) {
        setStatusMessage("Invalid JSON provided in the static rules text area.");
        return;
      }
    }

    setIsLoading(true);
    setStatusMessage("Requesting presigned URL...");

    const params = new URLSearchParams();
    params.append("file_name", uploadedFile.name);
    params.append("upload", "True");
    params.append("json_rules", JSON.stringify(rulesDict));

    if (staticRulesDict) {
      params.append("json_static_rules", JSON.stringify(staticRulesDict));
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
      });

      const sraResponse = await axios.get(`${BASE_URL}?${sraParams.toString()}`);
      if (sraResponse.status === 200) {
        setSraDownloadUrl(sraResponse.data.url);
        if (sraResponse.data.mappings) {
          // **Change 2:** Set SRA mappings separately
          setSraMappingsJson(sraResponse.data.mappings); // Save SRA mappings
        }
      } else {
        setStatusMessage("Failed to fetch SRA download URL.");
      }

      const biosampleParams = new URLSearchParams({
        file_name: uploadedFile.name,
        upload: "False",
        uuid,
        sra: "False",
      });

      const biosampleResponse = await axios.get(`${BASE_URL}?${biosampleParams.toString()}`);
      if (biosampleResponse.status === 200) {
        setBiosampleDownloadUrl(biosampleResponse.data.url);
        if (biosampleResponse.data.mappings) {
          // **Change 3:** Set Biosample mappings separately
          setBiosampleMappingsJson(biosampleResponse.data.mappings); // Save Biosample mappings
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
      const response = await axios.get(url, {
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

        <button
          onClick={handleUploadAndProcess}
          disabled={isLoading}
          className="upload-button"
          aria-label="Upload and Process Button"
        >
          {isLoading ? "Processing..." : "Upload and Process"}
        </button>

        {statusMessage && <div className="status-message">{statusMessage}</div>}

        {uploadGood && (
          <>
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
          </>
        )}

        {/* **Change 4:** Display separate SRA mappings */}
        {sraMappingsJson && (
          <section className="json-display-section">
            <h3>SRA Mappings JSON</h3>
            <pre className="json-output">{JSON.stringify(sraMappingsJson, null, 4)}</pre>
          </section>
        )}

        {/* **Change 5:** Display separate Biosample mappings */}
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
