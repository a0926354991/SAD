// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getFirestore } from "firebase/firestore";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyC6goNjuzfHtHKj7aiyftoAaGGlUAnzy5c",
  authDomain: "ramen-map-ee7ce.firebaseapp.com",
  projectId: "ramen-map-ee7ce",
  storageBucket: "ramen-map-ee7ce.firebasestorage.app",
  messagingSenderId: "821839003781",
  appId: "1:821839003781:web:dd5e939fd65f55c52a29ec",
  measurementId: "G-WSF2WGZ3CB"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firestore
export const db = getFirestore(app);
