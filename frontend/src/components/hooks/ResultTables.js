import React from "react";

export function EntityTable({ entities }) {
  return (
    <div className="result-table-wrapper">
      <table className="result-table">
        <thead>
          <tr>
            <th>id</th>
            <th>title</th>
            <th>description</th>
          </tr>
        </thead>
        <tbody>
          {entities.map((item, idx) => (
            <tr key={idx}>
              <td>{item.id}</td>
              <td>{item.title}</td>
              <td>{item.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function RelationshipTable({ relationships }) {
  return (
    <div className="result-table-wrapper">
      <table className="result-table">
        <thead>
          <tr>
            <th>id</th>
            <th>source</th>
            <th>target</th>
            <th>description</th>
          </tr>
        </thead>
        <tbody>
          {relationships.map((item, idx) => (
            <tr key={idx}>
              <td>{item.id}</td>
              <td>{item.source}</td>
              <td>{item.target}</td>
              <td>{item.description}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}